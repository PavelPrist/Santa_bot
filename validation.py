# -*- coding: utf-8 -*-
import re


def validate_full_name(message):
    return re.fullmatch(
        r"[a-яА-ЯЁё]+\s+[a-яА-ЯЁё]+\s+[a-яА-ЯЁё]+",
        message
    )


def validate_telephone(message):
    return re.fullmatch(
        r"(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})",
        message
    )


