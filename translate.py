from deep_translator import GoogleTranslator

target_text = "计算机科学"
english_text = GoogleTranslator(source='auto', target='en').translate(target_text)
print(english_text)