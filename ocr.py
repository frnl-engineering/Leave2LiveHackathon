import cv2
import pytesseract
from pytesseract import Output
from langdetect import detect_langs

DEFAULT_LANG = "eng+ndl+urk+rus"


def get_tesseract_lang(detected_lang):
    dict = {
        "nl": "nld",
        "ru": "rus",
        "uk": "ukr",
        "en": "eng",
    }
    try:
        return dict[detected_lang]
    except KeyError:
        return "eng"


def read_text_from_image_path(image_path: str, lang=DEFAULT_LANG) -> (str, str):
    minimal_confidence = 20
    custom_config = r'-l {0} --psm 3'.format(lang)
    img = cv2.imread(image_path)

    results = pytesseract.image_to_data(img, output_type=Output.DICT, config=custom_config)
    res = ""

    # loop over each of the individual text localizations
    for i in range(0, len(results["text"])):
        # extract the bounding box coordinates of the text region from
        # the current result
        # x = results["left"][i]
        # y = results["top"][i]
        # w = results["width"][i]
        # h = results["height"][i]
        # extract the OCR text itself along with the confidence of the
        # text localization
        text = results["text"][i]
        conf = int(results["conf"][i])

        # filter out weak confidence text localizations
        if conf > minimal_confidence:
            # display the confidence and text to our terminal
            # print("Confidence: {}".format(conf))
            # print("Text: {}".format(text))
            # print("")
            if text == "" or text == "|" or text == "-" or text == "\\":
                continue
            if text.strip() != "":
                res += text + " "
            # strip out non-ASCII text so we can draw the text on the image
            # using OpenCV, then draw a bounding box around the text along
            # with the text itself

    #         cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    #         cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
    #                     1.0, (0, 0, 255), 2)
    # cv2.imshow('img', img)
    # cv2.waitKey(0)

    # we don't know the language during initial recognition, so we try to detect it
    languages = detect_langs(res)
    if lang == DEFAULT_LANG:
        # when we detected used language, we use it again to get more precise results
        return read_text_from_image_path(image_path=image_path, lang=get_tesseract_lang(languages[0].lang))
    return res, languages[0].lang

def test():
    print(read_text_from_image_path('./media/nl1.jpeg'))
    print(read_text_from_image_path('./media/nl2.jpeg'))
    print(read_text_from_image_path('./media/rus1.jpeg'))
    print(read_text_from_image_path('./media/ukr1.jpeg'))


if __name__ == '__main__':
    test()
