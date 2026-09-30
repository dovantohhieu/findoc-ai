from findoc.answer import check_citations


def test_bat_trich_dan_ngoai_khoang():
    assert check_citations("Ý A [1]. Ý B [7].", 5)["invalid"], "[7] với 5 context phải bị bắt"


def test_trich_dan_hop_le_thi_khong_bao():
    assert not check_citations("Ý A [1]. Ý B [5].", 5)["invalid"]
