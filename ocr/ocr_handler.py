


import easyocr
import cv2
import re

class TamakkanOCR:
    def __init__(self, use_gpu=False):
        self.reader = easyocr.Reader(['en'], gpu=use_gpu)
        self.valid_speeds = {"20", "30", "40", "50", "60", "70", "80", "90", "100", "110", "120"}

    def read_speed_sign(self, cropped_frame):
        if cropped_frame is None or cropped_frame.size == 0:
            return ""

        gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        results = self.reader.readtext(thresh, detail=0)
        detected_text = " ".join(results).strip().upper()

        # خلي فقط الأرقام
        detected_text = re.sub(r'[^0-9]', '', detected_text)

        # رجع فقط السرعات الصحيحة
        if detected_text in self.valid_speeds:
            return detected_text

        return ""
    
    
