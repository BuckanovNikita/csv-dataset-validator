"""Training-specific metadata independence, bounded repairs and class-aware cleanup."""

import pandas as pd
import pandera.pandas as pa
import pytest

from ed_killer import ValidationOptions, schema_for, validate_dataframe


def box(**changes):
    return {
        "image_name": "a.png",
        "image_path": "a.png",
        "instance_label": "cat",
        "bbox_x_tl": 0,
        "bbox_y_tl": 0,
        "bbox_x_br": 20,
        "bbox_y_br": 20,
        "split": "train",
        "image_width": 100,
        "image_height": 100,
        **changes,
    }


def validate(frame, **options):
    return validate_dataframe(
        frame, profile="clearml-yolo", options=ValidationOptions(emit_warnings=False, **options)
    )


@pytest.mark.parametrize(
    "metadata",
    [
        {"issue_state": "closed", "issue_text": 42},
        {"issue_state": "resolved", "issue_text": ""},
        {"issue_state": "", "issue_text": "unresolved"},
        {"instance_shape": "deleted", "task_id": {"arbitrary": "metadata"}},
        {"confidence": 99, "rotation": "bad", "attributes": "not JSON"},
        {"job_stage": "bad", "job_state": "bad", "task_completed": "bad", "occluded": []},
        {"task_name": 7, "annotation_id": -1, "frame_id": "bad", "z_order": 0.5},
        {"source_row_id": object(), "custom": object()},
    ],
)
def test_metadata_does_not_change_schema_or_validation(metadata):
    frame = pd.DataFrame([box(**metadata)], index=[7])
    before = frame.copy(deep=True)
    pd.testing.assert_frame_equal(schema_for("clearml-yolo").validate(frame, lazy=True), before)
    result = validate(frame)
    assert result.is_valid
    assert result.issues == ()
    pd.testing.assert_frame_equal(result.clean, before)
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("width,height", [(0, 20), (20, 0), (2, 20), (20, 2), (1, 3), (-1, 20)])
def test_minimum_box_dimensions_are_strict(width, height):
    result = validate(pd.DataFrame([box(bbox_x_br=width, bbox_y_br=height)]))
    assert result.broken_row_positions == (0,)
    issue = next(issue for issue in result.issues if issue.code == "invalid_box_area")
    assert "2" in issue.message


def test_dimensions_just_above_minimum_are_accepted():
    assert validate(pd.DataFrame([box(bbox_x_br=2.0001, bbox_y_br=2.0001)])).is_valid


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"bbox_x_tl": -9.999}, (0, 0, 20, 20)),
        ({"bbox_y_tl": -9.999}, (0, 0, 20, 20)),
        ({"bbox_x_br": 109.999}, (0, 0, 100, 20)),
        ({"bbox_y_br": 109.999}, (0, 0, 20, 100)),
        ({"bbox_x_tl": -9, "bbox_y_tl": -9, "bbox_x_br": 109, "bbox_y_br": 109}, (0, 0, 100, 100)),
    ],
)
def test_small_overflow_is_clipped_per_edge_without_mutating_input(changes, expected):
    frame = pd.DataFrame([box(**changes)], index=[11])
    before = frame.copy(deep=True)
    result = validate(frame)
    assert result.is_valid
    assert tuple(result.clean.iloc[0][list(expected_columns())]) == expected
    issue = next(issue for issue in result.issues if issue.code == "bbox_clipped")
    assert issue.severity == "warning"
    assert issue.row_position == 0
    assert set(issue.columns) == set(changes)
    assert "before" in issue.message.lower() and "after" in issue.message.lower()
    pd.testing.assert_frame_equal(frame, before)
    assert list(result.clean.index) == [11]
    repeated = validate(result.clean)
    assert repeated.is_valid
    assert not any(issue.code == "bbox_clipped" for issue in repeated.issues)
    pd.testing.assert_frame_equal(result.clean, repeated.clean)


def expected_columns():
    return ("bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br")


@pytest.mark.parametrize("edge", expected_columns())
@pytest.mark.parametrize("distance", [10, 10.001])
def test_overflow_at_or_above_ten_quarantines_image(edge, distance):
    coordinate = -distance if edge.endswith("tl") else 100 + distance
    frame = pd.DataFrame([box(**{edge: coordinate}), box(bbox_x_tl=30, bbox_x_br=50)])
    result = validate(frame)
    assert result.broken_row_positions == (0, 1)
    pd.testing.assert_frame_equal(result.broken, frame)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)


@pytest.mark.parametrize("left,right", [(98, 105), (99, 105), (101, 105)])
def test_clipping_cannot_leave_an_undersized_or_empty_box(left, right):
    result = validate(pd.DataFrame([box(bbox_x_tl=left, bbox_x_br=right)]))
    assert not result.is_valid
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)


def test_missing_dimensions_do_not_authorize_clipping():
    frame = pd.DataFrame([box(bbox_x_tl=-1)]).drop(columns=["image_width", "image_height"])
    result = validate(frame)
    assert not result.is_valid
    assert "upper_image_bounds" in result.skipped_checks
    assert any(issue.code == "negative_coordinate" for issue in result.issues)


def test_conflicting_dimensions_do_not_authorize_clipping():
    frame = pd.DataFrame([box(bbox_x_tl=-1, width=90, height=100)])
    result = validate(frame)
    assert not result.is_valid
    assert any(issue.code == "dimension_conflict" for issue in result.issues)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)


def test_real_image_dimensions_authorize_clipping(tmp_path):
    from PIL import Image

    Image.new("RGB", (20, 30)).save(tmp_path / "a.png")
    frame = pd.DataFrame([box(bbox_x_tl=-1, bbox_x_br=25)]).drop(columns=["image_width", "image_height"])
    result = validate(frame, check_images=True, base_dir=tmp_path)
    assert result.is_valid
    assert tuple(result.clean.iloc[0][list(expected_columns())]) == (0, 0, 20, 20)


def test_same_class_cleanup_keeps_first_despite_metadata_and_clipping():
    frame = pd.DataFrame(
        [box(bbox_x_tl="-1", bbox_x_br="20", task_id=1), box(task_id=2), box(bbox_x_br=19.99)],
        index=[5, 5, 2],
    )
    before = frame.copy(deep=True)
    result = validate(frame)
    assert result.clean_row_positions == (0,)
    assert result.broken_row_positions == (1, 2)
    assert result.clean.iloc[0]["bbox_x_tl"] == "0"
    assert result.clean.iloc[0]["bbox_x_br"] == "20"
    assert all(
        issue.related_rows == (0,) for issue in result.issues if issue.code in {"duplicate_row", "high_iou"}
    )
    pd.testing.assert_frame_equal(result.broken, before.iloc[[1, 2]])
    pd.testing.assert_frame_equal(frame, before)


def test_class_conflict_is_detected_before_same_class_pruning():
    # A overlaps B at 0.99; B overlaps C at 0.99, but A does not overlap C at 0.99.
    frame = pd.DataFrame([box(bbox_x_br=100), box(bbox_x_br=99), box(bbox_x_br=98.01, instance_label="dog")])
    result = validate(frame)
    assert result.clean.empty
    conflicts = [issue for issue in result.issues if issue.code == "class_conflict"]
    assert {issue.row_position for issue in conflicts} == {1, 2}
    assert not any(issue.code in {"duplicate_row", "high_iou"} for issue in result.issues)


def test_repair_warnings_are_not_claimed_for_quarantined_or_duplicate_rows():
    frame = pd.DataFrame([box(), box(bbox_x_tl=-1)])
    result = validate(frame)
    assert result.clean_row_positions == (0,)
    assert result.broken.iloc[0]["bbox_x_tl"] == -1
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)
    conflict = validate(pd.DataFrame([box(bbox_x_tl=-1), box(instance_label="dog")]))
    assert conflict.clean.empty
    assert not any(issue.code == "bbox_clipped" for issue in conflict.issues)


def test_different_classes_below_threshold_remain_distinct():
    result = validate(pd.DataFrame([box(), box(instance_label="dog", bbox_x_br=19)]))
    assert result.clean_row_positions == (0, 1)


def test_explicit_negatives_ignore_shape_and_metadata():
    frame = pd.DataFrame(
        [box(instance_label="", bbox_x_tl="", bbox_y_tl="", bbox_x_br="", bbox_y_br="", instance_shape="box")]
    )
    assert validate(frame).is_valid


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), "nan", True, "not a number"])
def test_nonfinite_or_malformed_coordinates_cannot_be_repaired(bad):
    frame = pd.DataFrame([box(bbox_x_tl=-1, bbox_x_br=bad), box(task_id=99)])
    result = validate(frame)
    assert result.broken_row_positions == (0, 1)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)
    pd.testing.assert_frame_equal(result.broken, frame)


def test_direct_schema_rejects_negative_coordinates_without_repair():
    frame = pd.DataFrame([box(bbox_x_tl=-1)])
    original = frame.copy(deep=True)
    with pytest.raises(pa.errors.SchemaErrors):
        schema_for("clearml-yolo").validate(frame, lazy=True)
    pd.testing.assert_frame_equal(frame, original)
    assert validate(frame).is_valid


def test_repaired_clean_cells_and_original_broken_rows_keep_duplicate_index_lineage():
    frame = pd.DataFrame(
        [
            box(bbox_x_tl="-1", bbox_x_br="020", extra="first"),
            box(image_name="b.png", image_path="b.png", bbox_x_tl="-10", extra="broken"),
            box(image_name="c.png", image_path="c.png", bbox_x_tl="00", extra="third"),
        ],
        index=[9, 9, 9],
    )
    before = frame.copy(deep=True)
    result = validate(frame)
    assert result.clean_row_positions == (0, 2)
    assert result.broken_row_positions == (1,)
    expected = before.iloc[[0, 2]].copy()
    expected.iat[0, expected.columns.get_loc("bbox_x_tl")] = "0"
    pd.testing.assert_frame_equal(result.clean, expected)
    pd.testing.assert_frame_equal(result.broken, before.iloc[[1]])
    pd.testing.assert_frame_equal(frame, before)
    assert [issue.row_position for issue in result.issues if issue.code == "bbox_clipped"] == [0]


@pytest.mark.parametrize("right,broken", [(98.999, ()), (99, (0, 1)), (99.001, (0, 1))])
def test_cross_class_default_threshold_is_inclusive(right, broken):
    result = validate(pd.DataFrame([box(bbox_x_br=100), box(bbox_x_br=right, instance_label="dog")]))
    assert result.broken_row_positions == broken


def test_same_class_removed_boxes_cannot_suppress_later_rows():
    frame = pd.DataFrame([box(bbox_x_br=10), box(bbox_x_tl=2, bbox_x_br=12), box(bbox_x_tl=4, bbox_x_br=14)])
    result = validate(frame, iou_threshold=0.6)
    assert result.clean_row_positions == (0, 2)
    assert result.broken_row_positions == (1,)


def test_cveta_keeps_small_boxes_and_does_not_clip_overflow():
    options = ValidationOptions(emit_warnings=False)
    small = pd.DataFrame([box(instance_shape="box", bbox_x_br=1, bbox_y_br=1)])
    assert validate_dataframe(small, profile="cveta2", options=options).is_valid
    overflow = pd.DataFrame([box(instance_shape="box", bbox_x_tl=-1)])
    result = validate_dataframe(overflow, profile="cveta2", options=options)
    assert not result.is_valid
    pd.testing.assert_frame_equal(result.broken, overflow)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)


@pytest.mark.parametrize("width,height", [(90, None), (None, 90)])
def test_partial_alternative_dimensions_cannot_hide_conflicts(width, height):
    frame = pd.DataFrame([box(width=width, height=height, bbox_x_br=105)])
    result = validate(frame)
    assert not result.is_valid
    assert any(issue.code == "dimension_conflict" for issue in result.issues)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)
    pd.testing.assert_frame_equal(result.broken, frame)


def test_partial_dimensions_conflicting_across_rows_prevent_all_repairs():
    frame = pd.DataFrame([box(image_width=90, image_height=None), box(bbox_x_br=105)])
    result = validate(frame)
    assert result.broken_row_positions == (0, 1)
    assert any(issue.code == "dimension_conflict" for issue in result.issues)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)
    pd.testing.assert_frame_equal(result.broken, frame)


@pytest.mark.parametrize("width,height", [(19, None), (None, 29)])
def test_partial_dimensions_must_agree_with_measured_size(tmp_path, width, height):
    from PIL import Image

    Image.new("RGB", (20, 30)).save(tmp_path / "a.png")
    frame = pd.DataFrame([box(image_width=width, image_height=height, bbox_x_br=25)])
    result = validate(frame, check_images=True, base_dir=tmp_path)
    assert not result.is_valid
    assert any(issue.code == "image_dimension_mismatch" for issue in result.issues)
    assert not any(issue.code == "bbox_clipped" for issue in result.issues)
    pd.testing.assert_frame_equal(result.broken, frame)


def test_agreeing_partial_dimension_does_not_block_repair():
    result = validate(pd.DataFrame([box(width=100, height=None, bbox_x_br=105)]))
    assert result.is_valid
    assert result.clean.iloc[0]["bbox_x_br"] == 100
