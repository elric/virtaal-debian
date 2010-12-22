#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008 Dieter Verfaillie <dieterv@optionexplicit.be>
# Copyright 2009-2010 Zuza Software Foundation
#
# (NOTE: LGPL)
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


import os
import sys


def _isofromlangid(langid):
    # ISO 639-1
    #    http://www.loc.gov/standards/iso639-2/
    # List of existing mui packs:
    #    http://www.microsoft.com/globaldev/reference/win2k/setup/Langid.mspx
    # List of known id's
    #    http://www.microsoft.com/globaldev/reference/lcid-all.mspx

    lcid = {1078:    'af',    # Afrikaans - South Africa
            1052:    'sq',    # Albanian - Albania
            1118:    'am',    # Amharic - Ethiopia
            1025:    'ar',    # Arabic - Saudi Arabia
            5121:    'ar',    # Arabic - Algeria
            15361:   'ar',    # Arabic - Bahrain
            3073:    'ar',    # Arabic - Egypt
            2049:    'ar',    # Arabic - Iraq
            11265:   'ar',    # Arabic - Jordan
            13313:   'ar',    # Arabic - Kuwait
            12289:   'ar',    # Arabic - Lebanon
            4097:    'ar',    # Arabic - Libya
            6145:    'ar',    # Arabic - Morocco
            8193:    'ar',    # Arabic - Oman
            16385:   'ar',    # Arabic - Qatar
            10241:   'ar',    # Arabic - Syria
            7169:    'ar',    # Arabic - Tunisia
            14337:   'ar',    # Arabic - U.A.E.
            9217:    'ar',    # Arabic - Yemen
            1067:    'hy',    # Armenian - Armenia
            1101:    'as',    # Assamese
            2092:    'az',    # Azeri (Cyrillic)
            1068:    'az',    # Azeri (Latin)
            1069:    'eu',    # Basque
            1059:    'be',    # Belarusian
            1093:    'bn_IN', # Bengali (India)
            2117:    'bn',    # Bengali (Bangladesh)
            5146:    'bs',    # Bosnian (Bosnia/Herzegovina)
            1026:    'bg',    # Bulgarian
            1109:    'my',    # Burmese
            1027:    'ca',    # Catalan
            1116:    None,    # Cherokee - United States
            2052:    'zh_CN', # Chinese - People's Republic of China
            4100:    'zh',    # Chinese - Singapore
            1028:    'zh_TW', # Chinese - Taiwan
            3076:    'zh_HK', # Chinese - Hong Kong SAR
            5124:    'zh',    # Chinese - Macao SAR
            1050:    'hr',    # Croatian
            4122:    'hr',    # Croatian (Bosnia/Herzegovina)
            1029:    'cs',    # Czech
            1030:    'da',    # Danish
            1125:    'dv',    # Divehi
            1043:    'nl',    # Dutch - Netherlands
            2067:    'nl',    # Dutch - Belgium
            1126:    None,    # Edo
            1033:    'en',    # English - United States
            2057:    'en_UK', # English - United Kingdom
            3081:    'en',    # English - Australia
            10249:   'en',    # English - Belize
            4105:    'en_CA', # English - Canada
            9225:    'en',    # English - Caribbean
            15369:   'en',    # English - Hong Kong SAR
            16393:   'en',    # English - India
            14345:   'en',    # English - Indonesia
            6153:    'en',    # English - Ireland
            8201:    'en',    # English - Jamaica
            17417:   'en',    # English - Malaysia
            5129:    'en',    # English - New Zealand
            13321:   'en',    # English - Philippines
            18441:   'en',    # English - Singapore
            7177:    'en_ZA', # English - South Africa
            11273:   'en',    # English - Trinidad
            12297:   'en',    # English - Zimbabwe
            1061:    'et',    # Estonian
            1080:    'fo',    # Faroese
            1065:    'fa',    # Persian
            1124:    'fil',   # Filipino #XXX: GTK uses Tagalog (tl)
            1035:    'fi',    # Finnish
            1036:    'fr',    # French - France
            2060:    'fr',    # French - Belgium
            11276:   'fr',    # French - Cameroon
            3084:    'fr',    # French - Canada
            9228:    'fr',    # French - Democratic Rep. of Congo
            12300:   'fr',    # French - Cote d'Ivoire
            15372:   'fr',    # French - Haiti
            5132:    'fr',    # French - Luxembourg
            13324:   'fr',    # French - Mali
            6156:    'fr',    # French - Monaco
            14348:   'fr',    # French - Morocco
            58380:   'fr',    # French - North Africa
            8204:    'fr',    # French - Reunion
            10252:   'fr',    # French - Senegal
            4108:    'fr',    # French - Switzerland
            7180:    'fr',    # French - West Indies
            1122:    'fy',    # Frisian - Netherlands
            1127:    'fub',   # Fulfulde - Nigeria
            1071:    'mk',    # FYRO Macedonian
            2108:    'ga',    # Gaelic (Ireland)
            1084:    'gd',    # Gaelic (Scotland)
            1110:    'gl',    # Galician
            1079:    'ka',    # Georgian
            1031:    'de',    # German - Germany
            3079:    'de',    # German - Austria
            5127:    'de',    # German - Liechtenstein
            4103:    'de',    # German - Luxembourg
            2055:    'de',    # German - Switzerland
            1032:    'el',    # Greek
            1140:    'gn',    # Guarani - Paraguay
            1095:    'gu',    # Gujarati
            1128:    'ha',    # Hausa - Nigeria
            1141:    None,    # Hawaiian - United States
            1037:    'he',    # Hebrew
            1081:    'hi',    # Hindi
            1038:    'hu',    # Hungarian
            1129:    'ibb',    # Ibibio - Nigeria
            1039:    'is',    # Icelandic
            1136:    'ig',    # Igbo - Nigeria
            1057:    'id',    # Indonesian
            1117:    'iu',    # Inuktitut
            1040:    'it',    # Italian - Italy
            2064:    'it',    # Italian - Switzerland
            1041:    'ja',    # Japanese
            1099:    'kn',    # Kannada
            1137:    'kr',    # Kanuri - Nigeria
            2144:    'ks',    # Kashmiri
            1120:    'ks',    # Kashmiri (Arabic)
            1087:    'kk',    # Kazakh
            1107:    'km',    # Khmer
            1111:    'knn',   # Konkani
            1042:    'ko',    # Korean
            1088:    'ky',    # Kyrgyz (Cyrillic)
            1108:    'lo',    # Lao
            1142:    'la',    # Latin
            1062:    'lv',    # Latvian
            1063:    'lt',    # Lithuanian
            1086:    'ms',    # Malay - Malaysia
            2110:    'ms',    # Malay - Brunei Darussalam
            1100:    'ml',    # Malayalam
            1082:    'mt',    # Maltese
            1112:    'mni',   # Manipuri
            1153:    'mi',    # Maori - New Zealand
            1102:    'mr',    # Marathi
            1104:    'mn',    # Mongolian (Cyrillic)
            2128:    'mn',    # Mongolian (Mongolian)
            1121:    'ne',    # Nepali
            2145:    'ne',    # Nepali - India
            1044:    'no',    # Norwegian (Bokmￃﾥl)
            2068:    'no',    # Norwegian (Nynorsk)
            1096:    'or',    # Oriya
            1138:    'om',    # Oromo
            1145:    'pap',   # Papiamentu
            1123:    'ps',    # Pashto
            1045:    'pl',    # Polish
            1046:    'pt_BR', # Portuguese - Brazil
            2070:    'pt',    # Portuguese - Portugal
            1094:    'pa',    # Punjabi
            2118:    'pa',    # Punjabi (Pakistan)
            1131:    'qu',    # Quecha - Bolivia
            2155:    'qu',    # Quecha - Ecuador
            3179:    'qu',    # Quecha - Peru
            1047:    'rm',    # Rhaeto-Romanic
            1048:    'ro',    # Romanian
            2072:    'ro',    # Romanian - Moldava
            1049:    'ru',    # Russian
            2073:    'ru',    # Russian - Moldava
            1083:    None,    # Sami (Lappish)
            1103:    'sa',    # Sanskrit
            1132:    'nso',   # Northern Sotho
            3098:    'sr',    # Serbian (Cyrillic)
            2074:    'sr@latin',# Serbian (Latin)
            1113:    'sd',    # Sindhi - India
            2137:    'sd',    # Sindhi - Pakistan
            1115:    'si',    # Sinhalese - Sri Lanka
            1051:    'sk',    # Slovak
            1060:    'sl',    # Slovenian
            1143:    'so',    # Somali
            1070:    None,    # Sorbian
            3082:    'es',    # Spanish - Spain (Modern Sort)
            1034:    'es',    # Spanish - Spain (Traditional Sort)
            11274:   'es',    # Spanish - Argentina
            16394:   'es',    # Spanish - Bolivia
            13322:   'es',    # Spanish - Chile
            9226:    'es',    # Spanish - Colombia
            5130:    'es',    # Spanish - Costa Rica
            7178:    'es',    # Spanish - Dominican Republic
            12298:   'es',    # Spanish - Ecuador
            17418:   'es',    # Spanish - El Salvador
            4106:    'es',    # Spanish - Guatemala
            18442:   'es',    # Spanish - Honduras
            58378:   'es',    # Spanish - Latin America
            2058:    'es',    # Spanish - Mexico
            19466:   'es',    # Spanish - Nicaragua
            6154:    'es',    # Spanish - Panama
            15370:   'es',    # Spanish - Paraguay
            10250:   'es',    # Spanish - Peru
            20490:   'es',    # Spanish - Puerto Rico
            21514:   'es',    # Spanish - United States
            14346:   'es',    # Spanish - Uruguay
            8202:    'es',    # Spanish - Venezuela
            1072:    'st',    # Sutu
            1089:    'sw',    # Swahili
            1053:    'sv',    # Swedish
            2077:    'sv',    # Swedish - Finland
            1114:    'syc',   # Syriac
            1064:    'tg',    # Tajik
            1119:    None,    # Tamazight (Arabic)
            2143:    None,    # Tamazight (Latin)
            1097:    'ta',    # Tamil
            1092:    'tt',    # Tatar
            1098:    'te',    # Telugu
            1054:    'th',    # Thai
            2129:    'bo',    # Tibetan - Bhutan
            1105:    'bo',    # Tibetan - People's Republic of China
            2163:    'ti',    # Tigrigna - Eritrea
            1139:    'ti',    # Tigrigna - Ethiopia
            1073:    'ts',    # Tsonga
            1074:    'tn',    # Tswana
            1055:    'tr',    # Turkish
            1090:    'tk',    # Turkmen
            1152:    'ug',    # Uighur - China
            1058:    'uk',    # Ukrainian
            1056:    'ur',    # Urdu
            2080:    'ur',    # Urdu - India
            2115:    'uz@cyrillic',    # Uzbek (Cyrillic)
            1091:    'uz',    # Uzbek (Latin)
            1075:    've',    # Venda
            1066:    'vi',    # Vietnamese
            1106:    'cy',    # Welsh
            1076:    'xh',    # Xhosa
            1144:    None,    # Yi
            1085:    'yi',    # Yiddish
            1130:    'yo',    # Yoruba
            1077:    'zu',    # Zulu
    }

    return lcid.get(langid, None)

def get_win32_system_lang():
    from ctypes import windll
    langid = windll.kernel32.GetUserDefaultUILanguage()
    if not langid == 0:
        lang = _isofromlangid(langid) or 'C'
    else:
        lang = 'C'

    return lang

def _getlang():
    # Start with nothing
    lang = None

    # Try to detect language with GetUserDefaultUILanguage().
    # This supports windows MUI language packs and will return
    # the windows installation language if not available or
    # if the language has not been changed by the user.
    # Works on win2k and up.
    # Environment always overrides this for debugging purposes.
    lang = os.getenv('LANG')
    if lang is None:
        from ctypes import windll
        #windll.kernel32.GetUserDefaultUILanguage() - Windows UI language
        #windll.kernel32.GetUserDefaultLangID() - User's locale
        langid = windll.kernel32.GetUserDefaultLangID()
        if not langid == 0:
            lang = _isofromlangid(langid) or 'C'
        else:
            lang = 'C'

    return lang

def _putenv(name, value):
    # From python 2.4 on, os.environ changes only
    # work within python and no longer apply to low level
    # c stuff on win32. Lets force LANG so it works with
    # gtk+ etc
    from ctypes import windll
    kernel32 = windll.kernel32
    result = kernel32.SetEnvironmentVariableW(name, value)
    del kernel32
    if result == 0:
        raise

    from ctypes import cdll
    msvcrt = cdll.msvcrt
    result = msvcrt._putenv('%s=%s' % (name, value))
    del msvcrt

def fix_locale(lang=None):
    """This fixes some strange issues to ensure locale and gettext works
    correctly, also within glade, even with a non-default locale passed as
    parameter."""
    if sys.platform == 'win32':
        lang = lang or _getlang()

        _putenv('LANGUAGE', lang)

        os.environ['LANG'] = lang
        _putenv('LANG', lang)

        os.environ['LC_ALL'] = lang
        _putenv('LC_ALL', lang)
    if lang:
        # This is to support a non-locale UI language:
        os.environ['LANGUAGE'] = lang
