from __future__ import annotations

from app.models.intake import CaseGroup, IntakeCollectedFields
from app.models.triage import IncidentType
from app.services.case_grouping_service import group_case, group_requires_human_review


def assert_group(text: str, expected: CaseGroup) -> None:
    group, team, reason = group_case(IntakeCollectedFields(), text)

    assert group == expected
    assert team
    assert reason


def test_grouping_maps_requested_operational_groups() -> None:
    assert_group("น้ำท่วม มีคนติดอยู่", CaseGroup.RESCUE)
    assert_group("ผู้ป่วยหายใจลำบาก", CaseGroup.MEDICAL)
    assert_group("ไฟไหม้อาคาร มีควัน", CaseGroup.FIRE)
    assert_group("มีการทำร้ายและอันตรายสาธารณะ", CaseGroup.POLICE_PUBLIC_SAFETY)
    assert_group("นักท่องเที่ยวหลงทาง passport หาย", CaseGroup.TOURIST_SUPPORT)
    assert_group("ถนนขาด ไฟฟ้าดับ", CaseGroup.UTILITY_INFRASTRUCTURE)
    assert_group("ต้องการอาหาร น้ำดื่ม และที่พัก", CaseGroup.SHELTER_SUPPLIES)
    assert_group("อยากทำร้ายตัวเอง", CaseGroup.MENTAL_HEALTH_SUPPORT)
    assert_group("เสียงไม่ชัด", CaseGroup.UNKNOWN_HUMAN_REVIEW)


def test_flood_without_trapped_maps_to_flood_response() -> None:
    fields = IntakeCollectedFields(incident_type=IncidentType.FLOOD, location_text="หาดใหญ่")

    group, team, _ = group_case(fields, "น้ำท่วมอยู่ที่หาดใหญ่")

    assert group == CaseGroup.FLOOD
    assert team == "flood_response"


def test_unknown_and_mental_health_require_human_review() -> None:
    assert group_requires_human_review(CaseGroup.UNKNOWN_HUMAN_REVIEW) is True
    assert group_requires_human_review(CaseGroup.MENTAL_HEALTH_SUPPORT) is True
    assert group_requires_human_review(CaseGroup.FLOOD) is False
