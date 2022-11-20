from deep_translator import GoogleTranslator

def translate(text, target_lang="en"):
    return GoogleTranslator(source='auto', target=target_lang).translate(text)


def test():
    from ocr import read_text_from_image_path
    res = read_text_from_image_path('./media/nl1.jpeg')
    print(translate(res[0]))
    res = read_text_from_image_path('./media/nl2.jpeg')
    print(translate(res[0]))
    res = read_text_from_image_path('./media/rus1.jpeg')
    print(translate(res[0]))
    res = read_text_from_image_path('./media/ukr1.jpeg')
    print(translate(res[0]))


if __name__ == '__main__':
    test()