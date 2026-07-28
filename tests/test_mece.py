"""Phân nhóm MECE phải vét cạn và không mâu thuẫn với chính định nghĩa."""
import itertools

import pandas as pd
import pytest

from pxv import transform
from pxv.transform import classify_mece


@pytest.mark.parametrize("lead,hen,hd,expected", [
    (True,  True,  True,  transform.MECE_PERFECT),
    (True,  True,  False, transform.MECE_DROPPED),
    (True,  False, True,  transform.MECE_DIRECT),
    (True,  False, False, transform.MECE_NO_APPT),
    (False, True,  True,  transform.MECE_ORPHAN_APPT),
    (False, True,  False, transform.MECE_ORPHAN_APPT),
    (False, False, True,  transform.MECE_WALKIN),
    (False, False, False, transform.MECE_UNKNOWN),
])
def test_du_8_to_hop(lead, hen, hd, expected):
    assert classify_mece(lead, hen, hd) == expected


def test_vet_can_khong_bo_sot_to_hop_nao():
    labels = {classify_mece(*c) for c in itertools.product([True, False], repeat=3)}
    assert transform.MECE_UNKNOWN in labels, "chỉ tổ hợp rỗng mới được rơi vào 'Khác'"
    assert len(labels) == 7


def test_nhom_dat_hen_nhung_rot_khong_duoc_co_hoa_don():
    """Bug cũ: nhánh 'hẹn mồ côi' đặt CUỐI chuỗi if nên nuốt luôn tổ hợp
    (không lead + có hẹn + CÓ hóa đơn) vào Nhóm 4, khiến nhóm "rớt" lại có
    doanh thu — mâu thuẫn với chính tên của nó."""
    assert classify_mece(False, True, True) != transform.MECE_DROPPED


def test_master_khong_co_nhom_rot_nao_mang_doanh_thu(df_lead, df_hen, df_inv):
    m = transform.build_master(df_lead, df_hen, df_inv, pd.Timestamp("2026-01-01"))
    rot = m[m["Phân nhóm MECE"] == transform.MECE_DROPPED]
    assert rot["Doanh Thu (VNĐ)"].sum() == 0
    assert rot["Mã hóa đơn"].isna().all()


def test_master_khong_con_nhom_khac(df_lead, df_hen, df_inv):
    m = transform.build_master(df_lead, df_hen, df_inv, pd.Timestamp("2026-01-01"))
    assert (m["Phân nhóm MECE"] == transform.MECE_UNKNOWN).sum() == 0
