import os, urllib
basedir = os.path.abspath(os.path.dirname(__file__))

# SQLALCHEMY_DATABASE_URI = 'mssql+pymssql://sa:Heron7056@127.0.0.1:1433/Test'
SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://sa:Heron7056@127.0.0.1:1433/Test?driver=ODBC+Driver+13+for+SQL+Server'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = True

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'

OPENID_PROVIDERS = [
    { 'name': 'Shahriar', 'url': 'https://me.yahoo.com/a/Hfoz1x9xoPKpXG6ZPBxtvePD5Vq7yHsBR0xzSwOxOkEAEqRWQnppRMTgVe6TGm_VYzO9YII-' },
    { 'name': 'Varun', 'url': 'https://me.yahoo.com/a/ga2hLEoErf.aU6MxWpgYE17qtAthxFn00_LSqqSg_NbU6sYYBYHRCGYqyYeg1QsYyCKlm48-' },
    { 'name': 'George', 'url': 'https://me.yahoo.com/a/7cx1rjVxs.tqVBuZenRVjekU5jAbxqIZY7WOuPszYKvrYu_Nn48VQCzs2yXQNR7vLwLBfN8-' },
    { 'name': 'Eugene', 'url': 'https://me.yahoo.com/a/Mvs08dEih4HF6hEXEhrrqfdh2KveZpV26Lh0a2cLxgUG5QMVeQWsg5MtxwT00ZRLjqWxeKk-' },
    { 'name': 'Hong', 'url': 'https://me.yahoo.com/a/W7WGlIxog_FvdFM.WPcH1zsRPNer_XeOcZnFhOUqIMyTXReCKMjGGOcDcQC5xZYvMhX_YUE-' },
    { 'name': 'Qiang', 'url': 'https://me.yahoo.com/a/CddmH_phtf5wpSp4MytTYLPlE1YkySE5a40rM4pKy7Xas18XiayH40YduBFWwG_kOqZEMY0-' }]

# BOND
USP97475AN08 = 'Sovereign'
US040114GM64 = 'Warrant'
ARARGE03E139 = 'Sovereign'
USP97475AG56 = 'Sovereign'
GR0128012698 = 'Sovereign'
GR0138014809 = 'Warrant'
GRR000000010 = 'Sovereign'
GR0128013704 = 'Sovereign'
XS0501195134 = 'Sovereign'
USP7807HAK16 = 'Quasi'
XS0294364954 = 'Quasi'
XS0591549232 = 'Corporate'
US35671DAZ87 = 'Corporate'
USP7807HAR68 = 'Quasi'
USP7807HAT25 = 'Quasi'
ARARGE03F441 = 'Sovereign'
XS0808638612 = 'Corporate'
US91911TAH68 = 'Corporate'
XS1303927179 = 'Sovereign'
US105756BW95 = 'Sovereign'
GR0114028534 = 'Sovereign'
US195325BQ70 = 'Sovereign'
XS1298711729 = 'Corporate'
USN31738AB82 = 'Corporate'
USP18445AG42 = 'Corporate'
GR0138005716 = 'Sovereign'
XS0944707222 = 'Sovereign'
XS0908502452 = 'Corporate'
US91086QBG29 = 'Sovereign'
USL6366MAC75 = 'Corporate'
XS1028952403 = 'Sovereign'
XS0956935398 = 'Sovereign'
XS0209139244 = 'Warrant'
XS0114288789 = 'Sovereign'
XS1303925470 = 'Sovereign'
US91911TAP84 = 'Corporate'
US71654QBW15 = 'Quasi'
US105756BY51 = 'Sovereign'
XS0205545840 = 'Sovereign'
USP7807HAV70 = 'Quasi'
US105756BX78 = 'Sovereign'
XS1374118658 = 'Corporate'
US718286CB15 = 'Sovereign'
XS1422866456 = 'Provincial'
USN97716AA72 = 'Corporate'
US698299BE38 = 'Sovereign'
XS0356521160 = 'Corporate'
XS1571247656 = 'Corporate'
GR0133007204 = 'Sovereign'
USG6711KAA37 = 'Corporate'
GR0138007738 = 'Sovereign'
XS1571247490 = 'Corporate'
USG2585XAA75 = 'Corporate'
US66978CAB81 = 'Corporate'
USP84050AC02 = 'Corporate'
XS1261825621 = 'Corporate'
USP79171AE79 = 'Provincial'
XS1080330704 = 'Sovereign'
XS1577952952 = 'Sovereign'
XS1303929894 = 'Warrant'
XS1707041429 = 'Sovereign'
USP17625AB33 = 'Sovereign'
US91912EAA38 = 'Corporate'
USN64884AB02 = 'Corporate'
XS1558078496 = 'Sovereign'
US65412JAB98 = 'Sovereign'
US740840AC76 = 'Sovereign'
US91831AAC53 = 'Corporate'
US91911KAP75 = 'Corporate'
XS1126891685 = 'Quasi'
GR0114029540 = 'Sovereign'
USG6710EAQ38 = 'Corporate'
US040114HR43 = 'Sovereign'
GR0124034688 = 'Sovereign'
US03846JW552 = 'Sovereign'
US74514LE869 = 'Municipal'
XS1196517434 = 'Sovereign'
US591555AE76 = 'Corporate'
XS1533922933 = 'Corporate'
XS1589324075 = 'Corporate'
XS1533915721 = 'Corporate'
US745177FN05 = 'Municipal'
XS0294367205 = 'Quasi'
USP3699PGE18 = 'Sovereign'
US040114HQ69 = 'Sovereign'
US715638BM30 = 'Sovereign'
XS1775618439 = 'Sovereign'
XS1791939066 = 'Sovereign'
US745177EN14 = 'Municipal'
USP989MJBL47 = 'Quasi'
US698299BH68 = 'Sovereign'
GR0133011248 = 'Sovereign'
US760942BA98 = 'Sovereign'
US040114GK09 = 'Sovereign'
US745177EX95 = 'Municipal'
USY9384RAA87 = 'Sovereign'
USP7807HAM71 = 'Quasi'
USG6711KAC92 = 'Corporate'
USP84050AA46 = 'Corporate'
US900123CP36 = 'Sovereign'
USP7354PAA23 = 'Corporate'
USP78625DD22 = 'Quasi'
USP17625AD98 = 'Sovereign'
US71647NAM11 = 'Quasi'
US040114HN39 = 'Sovereign'
USP989MJBN03 = 'Quasi'
US626717AF90 = 'Corporate'
US040114HG87 = 'Sovereign'
XS1717011982 = 'Sovereign'

#EQUITY
US00653A1079 = 'Healthcare'
GRS015003007 = 'Financial Services'
US00887A1051 = 'Healthcare'
US1101221083 = 'Healthcare'
US2575541055 = 'Technology'
US4642872349 = 'ETF'
US4642882819 = 'ETF'
GRS359353000 = 'Utilities'
US3135867527 = 'Financial Services'
US3135867378 = 'Financial Services'
US3135861090 = 'Financial Services'
GRS145003000 = 'Utilities'
US4642885135 = 'ETF'
GRS245213004 = 'Financial Services'
US60937P1066 = 'Technology'
US56400P7069 = 'Healthcare'
US5951121038 = 'Technology'
GRS003003027 = 'Financial Services'
US6708515001 = 'Utilities'
GRS427003009 = 'Utilities'
US84652J1034 = 'Healthcare'
CA89620X5064 = 'Healthcare'
US9092143067 = 'Technology'
US9842451000 = 'Energy'
US37733W1053 = 'Healthcare'
US6976602077 = 'Utilities'
GRS003003035 = 'Financial Services'
US73328P1066 = 'Auto Manufacturers'
US8522341036 = 'Technology'
US4642867158 = 'ETF'

AR = 'Argentina'
DE = 'Germany'
GR = 'Greece'
PH = 'Philippines'
BR = 'Brazil'
VE = 'Venezuela'
UA = 'Ukraine'
US = 'United States'
RU = 'Russia'
KZ = 'Kazakhstan'
GB = 'United Kindom'
NL = 'Netherlands'
CH = 'Switzerland'
IL = 'Israel'
EC = 'Ecuador'
EG = 'Egypt'
NG = 'Nigeria'
JP = 'Japan'
AT = 'Austria'
CA = 'Canada'
CI = 'Ivory Coast'
CR = 'Costa Rica'
PE = 'Peru'
PR = 'Puerto Rico'
VN = 'Vietnam'
PA = 'Panama'
SA = 'Saudi Arabia'
TR = 'Turkey'
MX = 'Mexico'
UY = 'Uruguay'


YAHOO_FINANCE_EQUITY = {'US00653A1079' : 'https://finance.yahoo.com/quote/ADAP?p=ADAP', 
                    'GRS015003007' : 'https://finance.yahoo.com/quote/ALBKF?p=ALBKF', 
                    'US00887A1051' : 'https://finance.yahoo.com/quote/ALRN?p=ALRN', 
                    'US1101221083' : 'https://finance.yahoo.com/quote/BMY?p=BMY', 
                    'US2575541055' : 'https://finance.yahoo.com/quote/DOMO?p=DOMO', 
                    'US4642872349' : 'https://finance.yahoo.com/quote/EEM?p=EEM', 
                    'US4642882819' : 'https://finance.yahoo.com/quote/EMB?p=EMB', 
                    'US46429B4656' : 'https://finance.yahoo.com/quote/EWGS?p=EWGS', 
                    'GRS359353000' : 'https://finance.yahoo.com/quote/EYDAP.AT?p=EYDAP.AT', 
                    'US3135867378' : 'https://finance.yahoo.com/quote/FNMAT?p=FNMAT', 
                    'US3135867527' : 'https://finance.yahoo.com/quote/FNMAS?p=FNMAS', 
                    'US3135861090' : 'https://finance.yahoo.com/quote/FNMA?p=FNMA', 
                    'GRS145003000' : 'https://finance.yahoo.com/quote/GEKTERNA.AT?p=GEKTERNA.AT', 
                    'US37733W1053' : 'https://finance.yahoo.com/quote/GSK?p=GSK', 
                    'US4642885135' : 'https://finance.yahoo.com/quote/HYG?p=HYG', 
                    'GRS245213004' : 'https://finance.yahoo.com/quote/LAMDA.AT?p=LAMDA.AT', 
                    'US60937P1066' : 'https://finance.yahoo.com/quote/MDB?p=MDB', 
                    'US56400P7069' : 'https://finance.yahoo.com/quote/MNKD?p=MNKD', 
                    'GRS003003035' : 'https://finance.yahoo.com/quote/ETE.AT?p=ETE.AT', 
                    'GRS427003009' : 'https://finance.yahoo.com/quote/OLTH.AT?p=OLTH.AT', 
                    'US84652J1034' : 'https://finance.yahoo.com/quote/ONCE?p=ONCE', 
                    'CA89620X5064' : 'https://finance.yahoo.com/quote/TRIL?p=TRIL', 
                    'US9092143067' : 'https://finance.yahoo.com/quote/UIS?p=UIS', 
                    'US9842451000' : 'https://finance.yahoo.com/quote/YPF?p=YPF',
                    'US46434G7988' : 'https://finance.yahoo.com/quote/ERUS?p=ERUS',
                    'US5951121038' : 'https://finance.yahoo.com/quote/MU?p=MU',
                    'US6976602077' : 'https://finance.yahoo.com/quote/PAM?p=PAM',
                    'US73328P1066' : 'https://finance.yahoo.com/quote/POAHY?p=POAHY',
                    'US8522341036' : 'https://finance.yahoo.com/quote/SQ?p=SQ',
                    'US4642867158' : 'https://finance.yahoo.com/quote/TUR?p=TUR',
                    'US27826W1045' : 'https://finance.yahoo.com/quote/EVY?p=EVY&.tsrc=fin-srch',
                    'US6708515001' : 'https://finance.yahoo.com/quote/OIBR-C?p=OIBR-C',
                    'US69331C1080' : 'https://finance.yahoo.com/quote/PCG?p=PCG',
                    'CH0334081137' : 'https://finance.yahoo.com/quote/CRSP?p=CRSP',
                    'NL0011031208' : 'https://finance.yahoo.com/quote/MYL?p=MYL',
                    'US92839U2069' : 'https://finance.yahoo.com/quote/VC?p=VC',
                    'US1255231003' : 'https://finance.yahoo.com/quote/CI?p=CI',
                    'NL0013056914' : 'https://finance.yahoo.com/quote/ESTC?p=ESTC',
                    'PAL1201471A1' : 'https://finance.yahoo.com/quote/MDR?p=MDR',
                    'US5949181045' : 'https://finance.yahoo.com/quote/MSFT?p=MSFT',
                    'US6311031081' : 'https://finance.yahoo.com/quote/NDAQ?p=NDAQ',
                    'US92913A1007' : 'https://finance.yahoo.com/quote/PPR?p=PPR',
                    'US7475251036' : 'https://finance.yahoo.com/quote/QCOM?p=QCOM',
                    'US9286626000' : 'https://finance.yahoo.com/quote/VWAGY?p=VWAGY',
                    'US0382221051' : 'https://finance.yahoo.com/quote/AMAT?p=AMAT',
                    'US25271C1027' : 'https://finance.yahoo.com/quote/DO?p=DO',
                    'US02079K3059' : 'https://finance.yahoo.com/quote/GOOGL?p=GOOGL',
                    'US88579Y1010' : 'https://finance.yahoo.com/quote/MMM?p=MMM',
                    'US5949181045' : 'https://finance.yahoo.com/quote/MSFT?p=MSFT'   
                    }

REAL_TIME_EQUITY = {'US00653A1079' : 'https://finance.yahoo.com/quote/ADAP/history?p=ADAP', 
                    'GRS015003007' : 'https://finance.yahoo.com/quote/ALBKF/history?p=ALBKF', 
                    'US00887A1051' : 'https://finance.yahoo.com/quote/ALRN/history?p=ALRN', 
                    'US1101221083' : 'https://finance.yahoo.com/quote/BMY/history?p=BMY', 
                    'US2575541055' : 'https://finance.yahoo.com/quote/DOMO/history?p=DOMO', 
                    'US4642872349' : 'https://finance.yahoo.com/quote/EEM/history?p=EEM', 
                    'US4642882819' : 'https://finance.yahoo.com/quote/EMB/history?p=EMB', 
                    'US46429B4656' : 'https://finance.yahoo.com/quote/EWGS/history?p=EWGS', 
                    'GRS359353000' : 'https://finance.yahoo.com/quote/EYDAP.AT/history?p=EYDAP.AT', 
                    'US3135867378' : 'https://finance.yahoo.com/quote/FNMAT/history?p=FNMAT', 
                    'US3135867527' : 'https://finance.yahoo.com/quote/FNMAS/history?p=FNMAS', 
                    'US3135861090' : 'https://finance.yahoo.com/quote/FNMA/history?p=FNMA', 
                    'GRS145003000' : 'https://finance.yahoo.com/quote/GEKTERNA.AT/history?p=GEKTERNA.AT', 
                    'US37733W1053' : 'https://finance.yahoo.com/quote/GSK/history?p=GSK',
                    'US4642885135' : 'https://finance.yahoo.com/quote/HYG/history?p=HYG', 
                    'GRS245213004' : 'https://finance.yahoo.com/quote/LAMDA.AT/history?p=LAMDA.AT', 
                    'US60937P1066' : 'https://finance.yahoo.com/quote/MDB/history?p=MDB', 
                    'US56400P7069' : 'https://finance.yahoo.com/quote/MNKD/history?p=MNKD', 
                    'GRS003003035' : 'https://finance.yahoo.com/quote/ETE.AT/history?p=ETE.AT', 
                    'GRS427003009' : 'https://finance.yahoo.com/quote/OLTH.AT/history?p=OLTH.AT', 
                    'US84652J1034' : 'https://finance.yahoo.com/quote/ONCE/history?p=ONCE', 
                    'CA89620X5064' : 'https://finance.yahoo.com/quote/TRIL/history?p=TRIL', 
                    'US9092143067' : 'https://finance.yahoo.com/quote/UIS/history?p=UIS', 
                    'US9842451000' : 'https://finance.yahoo.com/quote/YPF/history?p=YPF',
                    'US46434G7988' : 'https://finance.yahoo.com/quote/ERUS/history?p=ERUS',
                    'US5951121038' : 'https://finance.yahoo.com/quote/MU/history?p=MU',
                    'US6976602077' : 'https://finance.yahoo.com/quote/PAM/history?p=PAM',
                    'US73328P1066' : 'https://finance.yahoo.com/quote/POAHY/history?p=POAHY',
                    'US8522341036' : 'https://finance.yahoo.com/quote/SQ/history?p=SQ',
                    'US4642867158' : 'https://finance.yahoo.com/quote/TUR/history?p=TUR',
                    'US27826W1045' : 'https://finance.yahoo.com/quote/EVY/history?p=EVY&.tsrc=fin-srch',
                    'US6708515001' : 'https://finance.yahoo.com/quote/OIBR-C/history?p=OIBR-C',
                    'US69331C1080' : 'https://finance.yahoo.com/quote/PCG/history?p=PCG',
                    'CH0334081137' : 'https://finance.yahoo.com/quote/CRSP/history?p=CRSP',
                    'NL0011031208' : 'https://finance.yahoo.com/quote/MYL/history?p=MYL',
                    'US92839U2069' : 'https://finance.yahoo.com/quote/VC/history?p=VC'}

REAL_TIME_FX = {'EUR':'https://finance.yahoo.com/quote/EURUSD=X',
                'ARS':'https://finance.yahoo.com/quote/ARSUSD=X',
                'AUD':'https://finance.yahoo.com/quote/AUDUSD=X'}

SCROLLING_TEXT = {'S&P 500':'https://finance.yahoo.com/quote/%5EGSPC/history?p=%5EGSPC',
                  'Dow 30':'https://finance.yahoo.com/quote/%5EDJI/history?p=%5EDJI',
                  'Nasdaq':'https://finance.yahoo.com/quote/%5EIXIC/history?p=%5EIXIC',
                  '10-Yr Bond':'https://finance.yahoo.com/quote/%5ETNX/history?p=%5ETNX',
                  'Nikkei 225':'https://finance.yahoo.com/quote/%5EN225/history?p=%5EN225',
                  'Hang Seng':'https://finance.yahoo.com/quote/%5EHSI/history?p=%5EHSI',
                  'DAX':'https://finance.yahoo.com/quote/%5EGDAXI/history?p=%5EGDAXI',
                  'VIX':'https://finance.yahoo.com/quote/%5EVIX/history?p=%5EVIX',
                  'EMB':'https://finance.yahoo.com/quote/EMB/history?p=EMB&.tsrc=fin-srch',
                  'EEM':'https://finance.yahoo.com/quote/EEM/history?p=EEM&.tsrc=fin-srch',
                  'HYG':'https://finance.yahoo.com/quote/HYG/history?p=HYG&.tsrc=fin-srch',
                  'MERVAL':'https://finance.yahoo.com/quote/%5EMERV/history?p=%5EMERV',
                  'IBOVESPA':'https://finance.yahoo.com/quote/%5EBVSP/history?p=%5EBVSP',
                  'EUR':'https://finance.yahoo.com/quote/EURUSD=X?p=EURUSD=X',
                  'GBP':'https://finance.yahoo.com/quote/GBPUSD%3DX?p=GBPUSD%3DX',
                  'JPY':'https://finance.yahoo.com/quote/JPY=X?p=JPY=X&.tsrc=fin-srch',
                  'BRL':'https://finance.yahoo.com/quote/BRL=X?p=BRL=X&.tsrc=fin-srch',
                  'ARS':'https://finance.yahoo.com/quote/ARS=X?p=ARS=X&.tsrc=fin-srch',
                  'MXN':'https://finance.yahoo.com/quote/MXN=X?p=MXN=X&.tsrc=fin-srch',
                  'CNY':'https://finance.yahoo.com/quote/CNY=X?p=CNY=X&.tsrc=fin-srch',
                  }


