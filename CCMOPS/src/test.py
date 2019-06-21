import pypyodbc
import pandas as pd

connection = pypyodbc.connect('Driver={SQL Server};'
                                  'Server=169.45.245.234;'
                                  'Database=racom201;'
                                  'uid=racom215;pwd=VLy8QiK1bz')
cursor = connection.cursor()

def get_tradelog(from_date,to_date):
    SQLcommand=("SPS_TRADELOG91 '{}','{}'".format(from_date, to_date))
    cursor.execute(SQLcommand)
    results = cursor.fetchall()
    return pd.DataFrame(results)

#df=get_tradelog('04/08/2019', '04/09/2019')


def get_price(price_date):
    SQLcommand=("SPS_Pricing99 '{}'".format(price_date))
    cursor.execute(SQLcommand)
    results = cursor.fetchall()
    return pd.DataFrame(results)

#df=get_price('04/10/2019')



def get_fxrates(price_date):
    SQLcommand=("SPS_FXRates99 '{}'".format(price_date))
    cursor.execute(SQLcommand)
    results = cursor.fetchall()
    return pd.DataFrame(results)

df=get_fxrates('04/10/2019')
print(df)

