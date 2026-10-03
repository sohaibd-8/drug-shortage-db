from iran_shortages.classifier import is_shortage_signal, guess_drug_name

def test_shortage_detection():
    assert is_shortage_signal("کمبود داروی سوتالول در بازار")
    assert is_shortage_signal("رفع کمبود دیلتیازم")
    assert not is_shortage_signal("کمبود آهن در نوجوانان")

def test_guess_drug():
    assert guess_drug_name("کمبود سوتالول؛ علت چیست؟") == "سوتالول"
