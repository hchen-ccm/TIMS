# -*- coding:utf-8 -*-
from flask import Flask, render_template, flash, redirect, g, abort, session, url_for, request,jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_openid import OpenID
from forms import LoginForm, TradeBlotterForm
from dao import db
from service import serviceImpl
from config import basedir        
from datetime import date 
from pymemcache.client.base import Client  
from threading import Lock
from flask_socketio import SocketIO  
from bs4 import BeautifulSoup
from collections import Counter  
from lxml import etree
import os, logging, csv, datetime, calendar, json, time, requests, eventlet, collections
from django.contrib.admin.templatetags.admin_list import ResultList
# new package import by jiahao_Ren
import numpy as np
from datetime import timedelta
import operator
#from iexfinance.stocks import Stock

app = Flask(__name__)
app.config.from_object('config')

# config for login
app.config['SECRET_KEY'] = 'secret!'
# config for websocket
eventlet.monkey_patch(socket=True)
async_mode = 'eventlet'
socketio = SocketIO(app, async_mode=async_mode)
# config for web scraping
thread = None
thread_lock = Lock()
# config for cache
client = Client(('54.162.132.155', 11211))
# client = Client(('127.0.0.1', 11211))
# init sqlAlchemy
dbAlchemy = SQLAlchemy(app)
# init login module 
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'
# init openId module
oid = OpenID(app, os.path.join(basedir, 'tmp'))
str.decode('ascii').encode('utf-8')
# config for log file
logger = logging.getLogger(__name__)
logger.setLevel(level = logging.INFO)
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

@lm.user_loader
def load_user(id):
    from models import User, ROLE_USER, ROLE_ADMIN
    #return User.query.get(int(id))
    return redirect(url_for('openPosition'))

@app.before_request
def before_request():
    # init user module
    g.user = current_user
    # init service module
    g.service = serviceImpl.Service()
    # init database module
    g.dataBase = db.DbConn()
    g.random = 0
    g.fundCode = {"ANDROMEDA":"AGCF", "BALDR DRACO":"INC5", "HARTZ":"HART", "BALDR DRACO SERIES B":"INC0","PERSEUS":"PGOF",\
                  "ASPEN CREEK":"ACPT","GOLDEN TREE":"GTAM", "PETRUS TACTICAL":"PTAC"}
    g.ibFund = {"U1320604":"AGCF", "U1238201":"ACPT","U1681581":"PGOF","U1988095":"HART"}
    g.longTermGL = 0
    g.shortTermGL = 0 
    g.queryRealizedGL = 0
    g.reportDate = ''
    # global variable to save the last updated date
    g.lastUptDt = "Last Updated on " + str(g.dataBase.qPriceHistory()[0].priceDate)
    # global variable to save cash components
    g.cashComponent = g.service.getAvailCashFromReport()['Perseus']
    
@app.route('/index')
#@login_required
def main(): 
    try:
        # parse FX file into database
        g.service.fxRate()
    except IOError:
        logger.error("FX rate file does not exist!", exc_info = True)
        abort(401)
    print("FX Finish")
    
    # parse trade file into database
    if g.service.fileNotEmpty("BBG"):
        g.service.tradeList()
        g.service.dataParsingForBBG()
        g.service.fileMovement("BBG")
        print("BBG Finish")
    if g.service.fileNotEmpty("FX_TRADE"):
        g.service.fxList()
        g.service.dataParsingForFX()
    
    # parse price file into database
    if g.service.fileNotEmpty("PRICE"):
        g.service.priceUpdateFromBBG()
        print("PRICE Finish")
    
    # commit database
    g.dataBase.commitment()  
    
    return redirect(url_for('openPosition'))
  
@app.route('/test')
#@login_required
def test():
    account = 'PGOF' 
    countryLabelsList = list()
    countryWeightsList = list()
    positionListAll = list() 
    positionListCategory = list()
    positionListCountry = list() 
    positionListCurrency = list() 
    cashFlowList = list()
    monthlyCashFlowList = list() 
    # cumulative return list 
    returnList = [6.61,7.96,7.27,6.30]
    # monthly return list
    monthlyReturn = [6.61,1.26,-0.63,-0.91]
    returnListSinceInception = list()
    monthlyReturnSinceInception = list()
    accountValueYearStart = 17585080.79
    accountValueLastMonth = 18692244.79


    summary = db.frontSummary.FrontSummary()
    
    # calculate monthly return and cumulative return since inception based on database
    navA = g.dataBase.qAccountHistory(account)
    for i in range(1, len(navA)):
        monReturn = round((float(navA[i]) / float(navA[i-1]) - 1) * 100, 2)
        cumuReturn = round((float(navA[i]) / float(navA[0]) - 1) * 100, 2)
        monthlyReturnSinceInception.append(monReturn)
        returnListSinceInception.append(cumuReturn)
        
    # calculate expected cash flow
    currList = g.dataBase.qOpenPositionCurrencyByFundName(account)
    for i in currList:
        tempDict = {}
        tempDict['name'] = str(i)
        tempDict['data'] = [0,0,0,0,0,0,0,0,0,0,0,0]
#HELLO    EACH CURR HAS A DICT WITH TWO KEYS, 
        monthlyCashFlowList.append(tempDict)
    
    # get all the countries in open positions, 'ACCOUNT' 
    countryList = g.dataBase.qOpenPositionCountryByCriteria(account)
    # calculate summary
    g.service.summaryCalculate(summary, account)
    # calculate open positions
    g.service.positionListAdd(positionListAll, countryList, summary, account, 'all', cashFlowList, monthlyCashFlowList)
    # calculate open positions grouped by security type
    g.service.positionListAdd(positionListCategory, countryList, summary, account, 'securityType', cashFlowList, monthlyCashFlowList)
    # calculate open positions grouped by country
    g.service.positionListAdd(positionListCountry, countryList, summary, account, 'category2', cashFlowList, monthlyCashFlowList)
    # calculate open positions grouped by currency
    g.service.positionListAdd(positionListCurrency, countryList, summary, account, 'currType', cashFlowList, monthlyCashFlowList)
    # calculate portfolio constituents by country
    g.service.countryDistribution(countryList, countryLabelsList, countryWeightsList, summary, account)
    # calculate long-term and short-term g/l
    g.service.calRealizedGL()
    # save new account value into database
    g.service.updatePnlFromReport(summary.accountValue)
    pnlFromReport = g.dataBase.qReport()[0]
    
    # by jiahao_ren: analytical information
    analyticalData = g.service.analyticCalculator(positionListCategory)     
    BondPortfolioDuration = round(analyticalData['Bond Portfolio Duration'], 2)
    
    
    
    
    
    
    
    # append two lists monthlyReturnSinceInception and returnListSinceInception based on the return lists above
    months = (date.today().year - 2016) * 12 + (date.today().month - 4)
    monthsFromDB = months - len(returnList) - 1
    tempReturnList = list()
    monthlyReturnSinceInception = monthlyReturnSinceInception[ : monthsFromDB] + monthlyReturn
    startValue = returnListSinceInception[monthsFromDB - 1]
    cumuReturn = 1 + startValue / 100
    for i in range(len(monthlyReturn)):
        cumuReturn *= 1 + monthlyReturn[i] / 100
        tempReturnList.append(round(((cumuReturn - 1) * 100), 2)) 
    returnListSinceInception = returnListSinceInception[ : monthsFromDB] + tempReturnList
    
    # fill summary
    summary.realizedGL = format(int(g.longTermGL + g.shortTermGL), ',')
    summary.accountValue = format(int(summary.accountValue), ',')
    summary.cash = format(int(summary.cash), ',')
    summary.marketValue = format(int(summary.marketValue), ',')
    summary.costBasis = format(int(summary.costBasis), ',')
    summary.gainLoss = format(int(summary.gainLoss), ',')
    
    # get SP500 real-time price
    sp500CurrPrice = g.service.getSP500Price() 
    # generate return lists of EMB and SP500
    embReturnSin201605 = list()
    embReturnYTD = list()
    sp500ReturnSin201605 = list()
    sp500ReturnYTD = list()
    hyperLinkDict = app.config['YAHOO_FINANCE_EQUITY']
    embMonReturnSin201605 = [-0.26,3.60,1.47,1.82,0.31,-1.42,-4.36,1.30,1.48,2.02,0.28,1.59,0.83,-0.33,0.91,1.79,-0.09,0.33,0.01,\
                             0.75,-0.15,-2.24,0.23,-1.67,-1.12,-1.46,2.76,-2.12,1.78,-2.45,-0.61,1.4,4.76]
    embMonReturnYTD = [4.76]
    sp500MonPriceSin201605 = [3957.95,3968.21,4114.51,4120.29,4121.06,4045.89,4195.73,4278.66,4359.81,\
                             4532.93,4538.21,4584.82,4649.34,4678.36,4774.56,4789.18,4887.97,\
                             5002.03,5155.44,5212.76,5511.21,5308.09,5173.19,5193.04,5318.10,\
                             5350.83,5549.96,5730.80,5763.42,5369.49,5478.91,4984.22,5383.63,5399]
    sp500MonPriceYTD = [5383.63,5399]
    sp500MonPriceSin201605.append(float(sp500CurrPrice))
    sp500MonPriceYTD.append(float(sp500CurrPrice))
    monthEndDate = datetime.date(date.today().year, date.today().month, 1)
    embCurrPrice = g.dataBase.qPriceHistoryByPriceDate('US4642882819', date.today())[0].price
    embMonEndPrice = g.dataBase.qPriceHistoryByPriceDate('US4642882819', monthEndDate)[0].price
    embMonReturn = round((float(embCurrPrice) - float(embMonEndPrice)) / float(embMonEndPrice) * 100, 2)
    embMonReturnSin201605.append(embMonReturn)
    embMonReturnYTD.append(embMonReturn)
    cumuReturn = 1
    for i in range(len(embMonReturnSin201605)):
        cumuReturn *= 1 + embMonReturnSin201605[i] / 100
        embReturnSin201605.append(round(((cumuReturn - 1) * 100), 2))
    cumuReturn = 1    
    for i in range(len(embMonReturnYTD)):
        cumuReturn *= 1 + embMonReturnYTD[i] / 100
        embReturnYTD.append(round(((cumuReturn - 1) * 100), 2))
    
    for i in range(1, len(sp500MonPriceSin201605)):
        cumuReturn = (sp500MonPriceSin201605[i] - sp500MonPriceSin201605[0]) / sp500MonPriceSin201605[0] * 100
        sp500ReturnSin201605.append(round(cumuReturn, 2))
    for i in range(1, len(sp500MonPriceYTD)):
        cumuReturn = (sp500MonPriceYTD[i] - sp500MonPriceYTD[0]) / sp500MonPriceYTD[0] * 100
        sp500ReturnYTD.append(round(cumuReturn, 2))
    
    currentDate = g.dataBase.qTopPriceDateInPriceHistory()[0]
    previousDate = g.dataBase.qTopPriceDateInPriceHistory()[1]
    # calculate daily income attribution
    returnListDTD = g.service.incomeAttribution(account, previousDate, currentDate)
    # calculate MTD income attribution
    returnListMTD = g.service.incomeAttributionMTD()
    # calculate YTD income attribution
    returnListYTD = g.service.incomeAttributionYTD()
    # calculate daily, MTD and YTD pnls
    dtdPnl, mtdPnl, ytdPnl = 0, 0, 0
    for i in returnListDTD[0]['details']:
        dtdPnl += int(i['Total'])
    for i in returnListMTD[0]['details']:
        mtdPnl += i['Total']
    for i in returnListYTD[0]['details']:
        ytdPnl += i['Total']
    # append monthly return and cumulative return
    currReturn = float(mtdPnl) / float(pnlFromReport.currAccValue - mtdPnl)
    if len(returnList) == 0:
        accReturn = currReturn
    else:
        accReturn = (1 + currReturn) * (1 + returnList[-1]/100) - 1
    returnList.append(round(accReturn * 100, 2))
    monthlyReturn.append(round(currReturn * 100, 2))
    # calculate YTD unrealized g/l
    client.set('unrealized_GL_YTD', int(accountValueYearStart * accReturn - g.longTermGL - g.shortTermGL))
    summary.gainLossYTD = int(accountValueYearStart * accReturn - g.longTermGL - g.shortTermGL)
    
    # calculate percentage of daily, monthly and yearly P/L
    dailyPnlPercent = str(round(float(dtdPnl) / float(pnlFromReport.currAccValue - dtdPnl) * 100, 2))
    monthlyPnlPercent = str(round(float(mtdPnl) / float(pnlFromReport.currAccValue - mtdPnl) * 100, 2))
    yearlyPnlPercent = str(round(float(ytdPnl) / float(pnlFromReport.currAccValue - ytdPnl) * 100, 2))
    summary.dailyPNL = format(dtdPnl, ',') + ' / ' + dailyPnlPercent + '%'
    summary.monthlyPNL = format(mtdPnl, ',') + ' / ' + monthlyPnlPercent + '%'
    summary.gainLossSumYTD = format(ytdPnl, ',') + ' / ' + yearlyPnlPercent + '%'

    # generate yearly return list    
    annualReturn = [10.56, 13.55, -12.28]
    cumuAnnualReturn = [10.56, 25.54, 10.01]
    tempReturn = round(float(ytdPnl) / float(pnlFromReport.currAccValue - ytdPnl) * 100, 2)
    annualReturn.append(tempReturn)
    cumuAnnualReturn.append(round(((1 + cumuAnnualReturn[-1]/100) * (1 + tempReturn/100) - 1) * 100, 2))
    
    x = positionListCategory[0]
    
    portfolioCarry=g.service.portforlioCarryComputation(positionListCategory)
    portfolioAnnualizedCarry=round(portfolioCarry/float(summary.accountValue.replace(',',''))*100,2)
    
    scrollDict = {}
    
    # save info into cache
    client.set('positionListAll', positionListAll)
    client.set('positionListCategory', positionListCategory)
    client.set('positionListCountry', positionListCountry)
    client.set('positionListCurrency', positionListCurrency)
    client.set('countryWeightsList', countryWeightsList)
    client.set('countryLabelsList', countryLabelsList)
    client.set('cashFlowList', cashFlowList)
    client.set('monthlyCashFlowList', monthlyCashFlowList)
    client.set('returnList', returnList)
    client.set('monthlyReturn', monthlyReturn)
    client.set('returnListIncep', returnListSinceInception)
    client.set('monthlyReturnIncep', monthlyReturnSinceInception) 
    client.set('shortTermGL', int(g.shortTermGL))
    client.set('longTermGL', int(g.longTermGL))
    client.set('accountValue', summary.accountValue) 
    client.set('cash', summary.cash)
    client.set('marketValue', summary.marketValue)
    client.set('costBasis', summary.costBasis)
    client.set('gainLoss', summary.gainLoss)
    client.set('gainLossSumYTD', summary.gainLossSumYTD)  
    client.set('dailyPNL', summary.dailyPNL) 
    client.set('monthlyPNL', summary.monthlyPNL)
    client.set('gainLossYTD', summary.gainLossYTD)
    client.set('portfolioAnnualizedCarry',portfolioAnnualizedCarry)
    client.set('embReturnSin201605', embReturnSin201605)
    client.set('embReturnYTD', embReturnYTD)
    client.set('sp500ReturnSin201605', sp500ReturnSin201605)
    client.set('sp500ReturnYTD', sp500ReturnYTD)
    client.set('returnListDTD', returnListDTD)
    client.set('returnListMTD', returnListMTD)
    client.set('returnListYTD', returnListYTD)
    client.set('annualReturn', annualReturn)
    client.set('cumuAnnualReturn', cumuAnnualReturn)
    client.set('scrollDict', scrollDict)
    client.set('BondPortfolioDuration', BondPortfolioDuration)
    
    # calculate FX exposure
    openPositions = eval(client.get('positionListAll'))[0]['details']
    cashList = eval(client.get('positionListAll'))[1]['details']
    fxExpoList = []
    tempEurDict, tempArsDict, tempGbpDict = {}, {}, {}
    tempEurDict['class'], tempEurDict['categoryName'] = 'EUR', 'EUR'
    tempEurDict['details'] = []
    tempArsDict['class'], tempArsDict['categoryName'] = 'ARS', 'ARS'
    tempArsDict['details'] = []
    tempGbpDict['class'], tempGbpDict['categoryName'] = 'GBP', 'GBP'
    tempGbpDict['details'] = []
    totalExpo = 0
    for op in openPositions:
        if op['Currency'] == 'EUR':
            totalExpo += op['MarketValue']
            tempEurDict['details'].append(op)
        elif op['Currency'] == 'ARS':
            totalExpo += op['MarketValue']
            tempArsDict['details'].append(op)
        elif op['Currency'] == 'USD' and op['Category'] == 'FUT' and op['Issuer'].find('EC'):
            op['MarketValue'] = int(op['Quantity'] * op['Price'])
            totalExpo += op['MarketValue']
            tempEurDict['details'].append(op)
    for cash in cashList:
        if cash['Currency'] == 'EUR':
            totalExpo += cash['MarketValue']
            tempEurDict['details'].append(cash)
        elif cash['Currency'] == 'ARS':
            totalExpo += cash['MarketValue']
            tempArsDict['details'].append(cash)
        elif cash['Currency'] == 'GBP':
            totalExpo += cash['MarketValue']
            tempGbpDict['details'].append(cash)
    for temp in tempEurDict['details']:
        temp['Weight'] = round(float(temp['MarketValue']) * 100 / float(totalExpo), 2)
    for temp in tempArsDict['details']:
        temp['Weight'] = round(float(temp['MarketValue']) * 100 / float(totalExpo), 2)
    for temp in tempGbpDict['details']:
        temp['Weight'] = round(float(temp['MarketValue']) * 100 / float(totalExpo), 2)
    fxExpoList.append(tempEurDict)
    fxExpoList.append(tempArsDict)
    fxExpoList.append(tempGbpDict)
    client.set('fxExpoList', fxExpoList)
        
    return redirect(url_for('openPosition'))

@app.route('/', methods=['GET', 'POST'])
@app.route('/op', methods=['GET', 'POST'])
#@login_required
def openPosition():
    account = request.args.get('account')
    group = request.args.get('group')
    if account == None:
        account = "PGOF"
    if group == None:
        group = "all"
    
    if group == 'all':
        positionList = client.get('positionListAll')
    elif group == 'securityType':
        positionList = client.get('positionListCategory')
    elif group == 'category2':
        positionList = client.get('positionListCountry')
    else:
        positionList = client.get('positionListCurrency')
    
    hyperLinkDict = app.config['YAHOO_FINANCE_EQUITY']
     
    return render_template("openPosition_flexibleTable.html", title = 'Open Position', positionList = positionList, 
                           country_weights_list = client.get('countryWeightsList'), 
                           country_labels_list = client.get('countryLabelsList'), account = account, 
                           group = group, cashFlowList = client.get('cashFlowList'), 
                           monthlyCashFlow = client.get('monthlyCashFlowList'), returnList = client.get('returnList'), 
                           monthlyReturn = client.get('monthlyReturn'), shortTermGL = client.get('shortTermGL'), 
                           longTermGL = client.get('longTermGL'), cash_component = g.cashComponent, lastUptDt = g.lastUptDt,
                           accountValue =  client.get('accountValue'), cash = client.get('cash'), 
                           marketValue = client.get('marketValue'), costBasis = client.get('costBasis'),
                           gainLoss = client.get('gainLoss'), gainLossSumYTD = client.get('gainLossSumYTD'),
                           dailyPNL = client.get('dailyPNL'), monthlyPNL = client.get('monthlyPNL'), \
                           gainLossYTD = client.get('gainLossYTD'), hyperLinkDict = hyperLinkDict, \
                           monthlyReturnIncep = client.get('monthlyReturnIncep'), returnListIncep = client.get('returnListIncep'), \
                           embReturnSince201605 = client.get('embReturnSin201605'), embReturnYTD = client.get('embReturnYTD'), \
                           sp500ReturnSin201605 = client.get('sp500ReturnSin201605'), sp500ReturnYTD = client.get('sp500ReturnYTD'), \
                           fxExpoList = client.get('fxExpoList'), scrollDict = client.get('scrollDict'), async_mode=socketio.async_mode, \
                           annualReturn = client.get('annualReturn'), cumuAnnualReturn = client.get('cumuAnnualReturn'),portfolioAnnualizedCarry=client.get('portfolioAnnualizedCarry'),\
                           BondPortfolioDuration = client.get('BondPortfolioDuration'))

@app.route('/riskReport', methods=['GET', 'POST'])
#@login_required
def riskReport():   
    openPositions = eval(client.get('positionListAll'))[0]['details'] 
    incomeAttrs = eval(client.get('returnListDTD'))[0]['details']
    bondConstituteList = g.service.bondPerformanceForRisk(openPositions, incomeAttrs)
    eqtyConstituteList = g.service.eqtyPerformanceForRisk(openPositions, incomeAttrs)
    
    tempBondDict = {}
    tempEqtyDict = {}
    
    for op in openPositions:
        if op['Category'] == 'BOND' or op['Category'] == 'BOND (defaulted)':
            tempBondDict[g.dataBase.qSecurityByISIN(op['ISIN'])[0].securityName] = op['DTDPxChg']
        elif op['Category'] == 'EQTY':
            tempEqtyDict[op['Issuer']] = op['DTDPxChg']
    
    nameList = []
    pxList = []
    b = Counter(tempBondDict)
    e = Counter(tempEqtyDict)
    i = 0
    for k, v in b.most_common(len(tempBondDict)):
        if i < 3:
            nameList.append(str(k))
            pxList.append(str(v) + '%')
        if i > len(tempBondDict) - 4:
            nameList.append(str(k))
            pxList.append(str(v) + '%')
        i += 1
    i = 0
    for k, v in e.most_common(len(tempEqtyDict)):
        if i < 3:
            nameList.append(str(k))
            pxList.append(str(v) + '%')
        if i > len(tempEqtyDict) - 4:
            nameList.append(str(k))
            pxList.append(str(v) + '%')
        i += 1
    
    return render_template("riskReport.html", bondConstituteList = bondConstituteList, eqtyConstituteList = eqtyConstituteList, \
                           lastUptDt = g.lastUptDt, nameList = nameList, pxList = pxList) 

@app.route('/trends', methods=['GET', 'POST'])
#@login_required
def trends():
    #HELLO    by jiahao_Ren: this part has been moved to serviceImpl (Dead Code for now)

    
#      allocate of all analyticTopic
    positionList = eval(client.get('positionListCategory'))
    ISINName = g.dataBase.qMap_ISIN_SecurityName()
    ISINName = np.array(ISINName)
    SecurityNo, SecurityName = ISINName.T
    ISINName = dict(zip(SecurityNo, SecurityName))

 
     
    for i in analyticTopic:
        eachBondValue = []
        if i == 'Bond Portfolio Duration' :
            data =[]
            for j in positionList:
                if j['categoryName'] == 'BOND':
                    data = j['details']
                    break
#                 declare the list first with exact length increase the speed
            eachBondValue = [None]*len(data)
            eachBondDuration = [None]*len(data)            
            for j in range(len(data)):
                eachBondValue[j] = float(data[j]['MarketValue'])
                eachBondDuration[j] = data[j]['Duration']
 
            BondPortfolioValue = sum(eachBondValue)
            eachBondValue = list(map(lambda x: x/float(BondPortfolioValue),  eachBondValue))
            
            BondPortfolioDuration = 0
            for j in range(len(data)):   
                BondPortfolioDuration += float(eachBondValue[j]) * float(eachBondDuration[j])
            analyticData[i] = BondPortfolioDuration
            
        if i == 'Bond Position annualized Volatility (1 month data)':    
            out = {}
            bondWeight = {}
            data = [] 
            for j in positionList:
                if j['categoryName'] == 'BOND':
                    data = j['details']
                    break
            for j in range(len(data)):
#                 print(data[j].keys())
                ISIN = data[j]['ISIN']
                weight = data[j]['Weight']
                securityName = ISINName[ISIN]
#                 use 21 days because represent monthly
                pricelist = g.dataBase.qPriceHistoryBtwDates(ISIN, date.today()-timedelta(days = 21), date.today())
                returnlist = []
#                 for bonds hold less than a month, ignore
                if len(pricelist) < 21: continue
                for i in range(len(pricelist)-1):
                    returnlist.append((pricelist[i+1]/pricelist[i])-1)
                out[securityName] = np.std(returnlist)*np.sqrt(252)
                bondWeight[securityName] = weight
#                 print(out)
            analyticData[i] = out
            bondWeight = sorted(bondWeight.items(), key=operator.itemgetter(1), reverse = True)
            data = []
            for j in range(len(bondWeight)):
                if bondWeight[j][0] not in out.keys(): continue
                templist = []
                templist.append(bondWeight[j][0])
                templist.append(out[bondWeight[j][0]])
                data.append(templist)

#HELLO END by jiahao_Ren     
    
    
    trendList = g.service.trendingData()
    return render_template("Trends.html" ,trendList=trendList)

@app.route('/incomeAttribution', methods=['GET', 'POST']) 
#@login_required
def incomeAttribution(): 
    return render_template("incomeAttribution.html", title = 'Income Attribution', returnList = client.get('returnListDTD'), \
                           returnListMTD = client.get('returnListMTD'), returnListYTD = client.get('returnListYTD'), \
                           lastUptDt = g.lastUptDt)
 
@app.route('/transView', methods=['GET', 'POST'])
#@login_required
def transView():
    
    form = FlaskForm()
    account = request.args.get('account')
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
    if account == None:
        account = "PGOF"
    if startDate == None:
        startDate = ""
    if endDate == None:  
        endDate = "" 
    if startDate != "" and endDate != "":
        listResult = g.dataBase.qTradeHistoryByDateRange(account, startDate, endDate)
        fxResult = g.dataBase.qTradeFxByDateRange(startDate, endDate)
        listResult = listResult + fxResult
    else:
        startDate = datetime.date(date.today().year, 1, 1)
        endDate = date.today()
        listResult = g.dataBase.qTradeHistoryByDateRange(account, startDate, endDate)
        fxResult = g.dataBase.qTradeFxByDateRange(startDate, endDate)
        listResult = listResult + fxResult
    return render_template("TransactionsView.html", title = 'Transactions', name = listResult, startDate = startDate, \
                           endDate = endDate, lastUptDt = g.lastUptDt)

@app.route('/transSearch', methods=['GET', 'POST'])
#@login_required
def transSearch():
    form = FlaskForm()
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
    criteria = str(request.args.get('criteria')).lower()
    if criteria == "bond":
        criteria = "EURO"
    if criteria == "equity":
        criteria = "EQTY"
    if criteria == "future":
        criteria = "FUT"
    listResult = g.dataBase.qFuzzyTradeHistory(criteria)
    fxResult = g.dataBase.qFuzzyTradeFx(criteria)
    listResult = listResult + fxResult
    resultList = g.service.summaryofTransactionFuzzySearch(criteria)
    if startDate == None:
        startDate = datetime.date(2016, 1, 1)
    if endDate == None:
        endDate = date.today()
    return render_template("TransactionSearch.html", title = 'Transactions', name = listResult, resultList=resultList, startDate = startDate, endDate = endDate)
    #return render_template("TransactionsView.html", title = 'Transactions', name = listResult, startDate = startDate, endDate = endDate)
@app.route('/gl', methods=['GET', 'POST'])
#@login_required
def realizedGL():
    form = FlaskForm() 
    account = request.args.get('account')
    if account == None:
        account = "PGOF"
    year = request.args.get('year') 
    month = request.args.get('month')
    if year == "" or year == None:
        year = "2019"
    if month == None:
        month = "0"
    realizedGLList = g.service.realizedGLDetails(year, month)
    openPositions = eval(client.get('positionListAll'))[0]['details']
    cashPositions = eval(client.get('positionListAll'))[1]['details']
    
    unrzGlList = []
    g.service.unRealizedDetails(unrzGlList, openPositions, cashPositions)
    
    unGL = format(int(client.get('unrealized_GL_YTD')), ',')

    return render_template("RealizedGLDetails.html", title = 'Gain/Loss', realizedGLList = realizedGLList, account = account, \
                           lastUptDt = g.lastUptDt, year = year, month = month, unGL = unGL, unrzGlList = unrzGlList)

@app.route('/sh', methods=['GET', 'POST'])
#@login_required
def shareholdersView():
    form = FlaskForm()
    account = request.args.get('account')
    investor = request.args.get('investor')
    year = request.args.get('year')
    month = request.args.get('month')
    if account == None:
        account = "PGOF"
    if investor == None:
        investor = "Shahriar"
    if year == "" or year == None:
        year = str(datetime.datetime.now().year)
    yearView = year
    if month == None:
        month = str(datetime.datetime.now().month - 1)
        if month == "0":
            month = "12"
            yearView = str(int(year) - 1)
    monthRange = calendar.monthrange(int(yearView), int(month))
    if int(month) < 10:
        dateStart = '0' + month + '/' + '01/' + yearView 
        dateEnd = '0' + month + '/' + str(monthRange[1]) + '/' + yearView
    else:
        dateStart = month + '/' + '01/' + yearView 
        dateEnd = month + '/' + str(monthRange[1]) + '/' + yearView
    if int(year) >= datetime.datetime.now().year and int(month) >= datetime.datetime.now().month:
        shareholders = db.frontInvestPNL.FrontInvestPNL()
    else:
        shareholders = g.service.shareholderDetails(account, investor, year, month)
        shareholders.subscriptionRange = format(shareholders.subscriptionRange, ',')
        shareholders.subscriptionYear = format(shareholders.subscriptionYear, ',')
        shareholders.redemptionRange = format(shareholders.redemptionRange, ',')
        shareholders.redemptionYear = format(shareholders.redemptionYear, ',')
        shareholders.accountValueYearStart = format(shareholders.accountValueYearStart, ',')
        shareholders.accountValueStartDt = format(shareholders.accountValueStartDt, ',')
        shareholders.accountValueEndDt = format(shareholders.accountValueEndDt, ',')
        shareholders.deltaAccountValue = format(shareholders.deltaAccountValue, ',')
        shareholders.deltaAccountValueYTD = format(shareholders.deltaAccountValueYTD, ',')
        shareholders.currReturn = str(shareholders.currReturn) + "%"
        shareholders.ytdReturn = str(shareholders.ytdReturn) + "%"
    valueList, colorList, categoryList = g.service.shareholdersChart(account, investor)
    return render_template("InvestorReport.html", title = 'Shareholders', investor = investor, account = account, \
                           year = year, month = month, shareholders = shareholders, dateStart = dateStart, dateEnd = dateEnd, \
                           valueList = valueList, colorList = colorList, categoryList = categoryList) 

@app.route('/sh2', methods=['GET', 'POST'])
#@login_required  
def shareholdersDetails():
    form = FlaskForm()
    account = request.args.get('account')
    investor = request.args.get('investor')
    if account == None:
        account = "PGOF"
    if investor == None:
        investor = "All"
    if investor == "All":
        investHistory, documentList = g.dataBase.qInvestHistory(account)
    else:
        investHistory, documentList = g.dataBase.qInvestHistoryByInvestorName(investor, account, "1900-01-01", "2099-12-31")
    return render_template("InvestorDetails.html", title = 'Shareholders', account = account, investHistory = investHistory, \
                           investor = investor, documentList = documentList)

'''
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('openPosition'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])
    return render_template('login.html', title='Sign In', form=form, providers=app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp):
    from models import User, ROLE_USER, ROLE_ADMIN
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = User(nickname=nickname, email=resp.email)
        dbAlchemy.session.add(user)
        dbAlchemy.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    return redirect(url_for('openPosition'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
'''
    
    
@app.route('/tb', methods=['GET', 'POST'])
@login_required
def tb():
    form = TradeBlotterForm()
    return render_template("TradeBlotter.html", title = 'Trader Blotter', form = form)

@app.route('/tb2', methods=['GET', 'POST'])
@login_required
def tb2():
    form = TradeBlotterForm()
    tb = db.tradeBlotter.TradeBlotter()
    securityList = list()
    tb.isin = request.args.get('isin')
    tb.tradeDate = request.args.get('date')
    tb.time = request.args.get('time')
    securityList = g.dataBase.qSecurityByISIN(tb.isin)
    if len(securityList) == 0:
        return render_template("TradeBlotter2.html", title = 'Trader Blotter', form = form, isin = tb.isin, myDate = tb.tradeDate, myTime = tb.time)
    else:
        sName = securityList[0].securityName
        currType = securityList[0].currType
        sType = securityList[0].securityType
        if sType == "EURO" or sType == "FUT":
            return render_template("TradeBlotter2.html", title = 'Trader Blotter', form = form, name = sName, isin = tb.isin, myDate = tb.tradeDate, myTime = tb.time, currType = currType, sType = sType)
        elif sType == "EQTY":
            return render_template("TradeBlotter2.html", title = 'Trader Blotter', form = form, name = sName, isin = tb.isin, myDate = tb.tradeDate, myTime = tb.time, currType = currType, sType2 = sType)
        else:
            return render_template("TradeBlotter2.html", title = 'Trader Blotter', form = form, name = sName, isin = tb.isin, myDate = tb.tradeDate, myTime = tb.time, currType = currType)

@app.route('/tbView', methods=['GET', 'POST'])
@login_required
def tbView():
    form = FlaskForm()
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
    if form.validate_on_submit():
        return redirect(url_for('tb'))
    if startDate == None:
        startDate = ""
    if endDate == None:
        endDate = ""
    if startDate != "" or endDate != "":
        if startDate == "":
            startDate = "0000-00-00"
        if endDate == "":
            endDate = "9999-99-99"
        listResult = g.dataBase.qTradeBlotterWithinDate(startDate, endDate)
    else:
        listResult = g.dataBase.qTradeBlotter()
    return render_template("TradeBlotterView.html", title = 'Trade Blotter', name = listResult, startDate = startDate, endDate = endDate)

@app.route('/tbSubmit', methods=['GET', 'POST'])
@login_required
def tbSubmit():
    form = TradeBlotterForm()
    tb = db.tradeBlotter.TradeBlotter()
    if form.validate_on_submit():
        tb.tradeDate = form['tradeDate'].data
        tb.time = form['time'].data
        tb.isin = form['isin'].data
        tb.securityName = form['securityName'].data
        tb.bs = form['bs'].data
        tb.quantity = form['quantity'].data
        tb.price = form['price'].data
        tb.currency = form['currency'].data
        tb.trader = str(form['trader'].data)
        tb.counterparty = form['counterparty'].data
        tb.salesTrader = form['salesTrader'].data
        tb.remark = form['remark'].data
        tb.status = "Applied"
        tb.book = form['book'].data
        tb.accounts = ""
        if form['AGCF'].data != "0":
            tb.accounts += "AGCF:" + form['AGCF'].data + " "
        if form['INC5'].data != "0":
            tb.accounts += "INC5:" + form['INC5'].data + " "
        if form['ACPT'].data != "0":
            tb.accounts += "ACPT:" + form['ACPT'].data + " "
        if form['PGOF'].data != "0":
            tb.accounts += "PGOF:" + form['PGOF'].data + " "
        if form['INC0'].data != "0":
            tb.accounts += "INC0:" + form['INC0'].data + " "
        if form['HART'].data != "0":
            tb.accounts += "HART:" + form['HART'].data
        g.dataBase.iTradeBlotter(tb)
        g.dataBase.commitment()
        listResult = g.dataBase.qTradeBlotter()
#         return render_template("TradeBlotterView.html", title = 'Trade Blotter', name = listResult)
        return redirect(url_for('tbView'))
    return render_template('TradeBlotter.html', title='ADD', form=form)

@app.route('/tbManage', methods=['GET', 'POST'])
@login_required
def tbManage():
    form = FlaskForm()
    listResult = g.dataBase.qTradeBlotterByStatus("Applied")
    p = Paginator(listResult, 10)
    pageNo = request.args.get('pageNo')
    try:
        result = p.page(pageNo)
    except PageNotAnInteger:
        result = p.page(1)
    except EmptyPage:
        result = p.page(p.num_pages)
    return render_template("TradeBlotterManage.html", title = 'Trade Blotter', name = result)

@app.route('/tbConfirm', methods=['GET', 'POST'])
@login_required
def tbConfirm():
    tb = db.tradeBlotter.TradeBlotter()
    tb.id = request.args.get('id')
    tb.status = "Granted"
    g.dataBase.uStatusInTradeBlotter(tb)
    return redirect(url_for('tbManage'))

# @app.teardown_request
# def teardown_request(exception):
#     print("SUCCESS")

@app.errorhandler(404)  
def not_found(e):
#     g.service.emailAutoSend("Unauthorized counterparty detected, stop procedure!")   
    return render_template("404.html", msg = "Unauthorized counterparty detected, stop procedure!")

@app.errorhandler(401)   
def not_found(e):
    return render_template("401.html", msg = "File does not exist!")

def background_thread():
    count=0 
    while count>=0:
        start_time = time.time()
        priceDict, fxDict, realTimeDtdPriceDict, realTimeMtdPriceDict, scrollDict = getPrice()
        socketio.emit('server_response',{'price':priceDict,'fx':fxDict,'dtdPrice':realTimeDtdPriceDict,\
                                         'mtdPrice':realTimeMtdPriceDict,'scrollPrice':scrollDict}, namespace = '/realTime')
        
        print('process ',count)
        print("--- %s seconds ---" % (time.time() - start_time))
        if count <20:
            socketio.sleep(10)
        elif count <50:
            socketio.sleep(300)
        else:
            socketio.sleep(3600)
        count+=1
        print("--- %s seconds including sleep ---" % (time.time() - start_time))

@app.route('/updateRealtimeEquityPrices', methods=['GET', 'POST'])
def updateRealtimeEquityPrices():
    start_time = time.time()
    exceptionList = ['FNMA Pfd','GKTRF','OLTH','LAMDA','SRV']
    replaceDict={'OIBR/C':'OIBR.C','place_holder':'placeHolder'}
    tickerList=[]
    priceList=[]
    resultDict={}
    positionList = eval(client.get('positionListCategory'))
    for dict in positionList:
        if dict['class']=='EQTY':
            for x in dict['details']:
                if x['Issuer'] not in exceptionList:
                    if x['Issuer'] in replaceDict.keys():
                        tickerList.append(replaceDict[x['Issuer']])
                    else:
                        tickerList.append(x['Issuer'])
    resultDict = {'tickers':tickerList}
    for ticker in tickerList:
        priceList.append(iexFinanceAPIStockPrice(ticker))
    resultDict ['prices']=priceList
    print("--- %s seconds to complete priceupdate ---" % (time.time() - start_time))
    return jsonify(resultDict)

def iexFinanceAPIStockPrice(ticker):
    try:
        stock = Stock(ticker, token="sk_d6410f49068d422fb3ffb8d25e14c7fc")
    except:
        stock = Stock(ticker, token="sk_aac489a80f854745b00a5432be3eb16d")
        
    return stock.get_price()

def iexFinanceAPIStockPriceStreaming(ticker):
    try:
        stock = Stock(ticker, token="sk_e1117a5e81cb4445a66d82623d65c30c")
        return stock.get_price()
    except:
        return 0
    

@app.route('/op2')
#@login_required
def openPositionRealTime(): 
    account = request.args.get('account')
    group = request.args.get('group') 
    if account == None: 
        account = "PGOF"
    if group == None:
        group = "securityType"
    if group == 'all':
        positionList = client.get('positionListAll')
    elif group == 'securityType':
        positionList = client.get('positionListCategory')
    elif group == 'category2':
        positionList = client.get('positionListCountry')
    else:
        positionList = client.get('positionListCurrency')

    hyperLinkDict = app.config['YAHOO_FINANCE_EQUITY']
    
    return render_template('openPosition_flexibleTable2.html', title = 'Open Position', positionList = positionList, 
                           country_weights_list = client.get('countryWeightsList'), 
                           country_labels_list = client.get('countryLabelsList'), account = account, 
                           group = group, cashFlowList = client.get('cashFlowList'), 
                           monthlyCashFlow = client.get('monthlyCashFlowList'), returnList = client.get('returnList'), 
                           monthlyReturn = client.get('monthlyReturn'), shortTermGL = client.get('shortTermGL'), 
                           longTermGL = client.get('longTermGL'), cash_component = g.cashComponent, lastUptDt = g.lastUptDt,
                           accountValue =  client.get('accountValue'), cash = client.get('cash'), 
                           marketValue = client.get('marketValue'), costBasis = client.get('costBasis'),
                           gainLoss = client.get('gainLoss'), gainLossSumYTD = client.get('gainLossSumYTD'),
                           dailyPNL = client.get('dailyPNL'), monthlyPNL = client.get('monthlyPNL'), \
                           gainLossYTD = client.get('gainLossYTD'), async_mode=socketio.async_mode, hyperLinkDict = hyperLinkDict, \
                           monthlyReturnIncep = client.get('monthlyReturnIncep'), returnListIncep = client.get('returnListIncep'), \
                           embReturnSince201605 = client.get('embReturnSin201605'), embReturnYTD = client.get('embReturnYTD'), \
                           sp500ReturnSin201605 = client.get('sp500ReturnSin201605'), sp500ReturnYTD = client.get('sp500ReturnYTD'), \
                           scrollDict = client.get('scrollDict'), annualReturn = client.get('annualReturn'), cumuAnnualReturn = client.get('cumuAnnualReturn'),\
                           portfolioAnnualizedCarry=client.get('portfolioAnnualizedCarry'))

@socketio.on('connect', namespace='/realTime')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)

def getPrice():
    realTimeDict = app.config['REAL_TIME_EQUITY']
    priceDict = {}
    fxDict = {}
    scrollDict = {}
    realTimeDtdPriceDict = {}
    realTimeMtdPriceDict = {}
    '''
    for ISIN, url in realTimeDict.items():
        soup = BeautifulSoup(requests.get(url).text, "lxml")
        trs = soup.find_all('tr')
        try:
            price = float(trs[1].find_all('span')[5].text)
            priceDict[ISIN] = round(price, 2)
        except:
            pass
    '''
    exceptionList = ['FNMA Pfd','GKTRF','OLTH','LAMDA','SRV']
    replaceDict={'OIBR/C':'OIBR.C','place_holder':'placeHolder'}
    tickerList=[]
    priceList=[]
    positionList = eval(client.get('positionListCategory'))
    for dict in positionList:
        if dict['class']=='EQTY':
            for x in dict['details']:
                if x['Issuer'] not in exceptionList:
                    if x['Issuer'] in replaceDict.keys():
                        tickerList.append(replaceDict[x['Issuer']])
                    else:
                        tickerList.append(x['Issuer'])
    tickerList=['ALRN']
    priceDict = {'tickers':tickerList}
    for ticker in tickerList:
        #priceList.append(iexFinanceAPIStockPriceStreaming(ticker))
        priceList.append(0.8226)
    priceDict ['prices']=priceList
   
    print('priceDict finished')

    fxUrlDict = app.config['REAL_TIME_FX']
    for curr, url in fxUrlDict.items():
        try:
            soup = BeautifulSoup(requests.get(url).text, "lxml")
            x=soup.find_all('table')
            bidtds = x[0].find_all('td')
            bid = bidtds[len(bidtds)-1].text
            asktds = x[0].find_all('td')
            ask = asktds[len(bidtds)-1].text
            fxDict[curr] = (float(bid) + float(ask)) / 2
        except:
            pass
    fxDict['USD'] = 1
    
    print('fxDict finished')
    '''
    with app.app_context():
        tempDB = g.dataBase = db.DbConn()
        isinListForEquity = tempDB.qISINFromSecurityForEquity()
        for ISIN in isinListForEquity:
            s = db.security.Security()
            s.ISIN = ISIN
            s.securityType = 'EQTY'
            currPrice = float(tempDB.qSecurityBySecurityName(s)[0].currPrice)
            realTimeDtdPriceDict[str(ISIN)] = currPrice
            try:
                realTimeMtdPriceDict[str(ISIN)] = float(tempDB.qPriceHistoryMonthEnd(ISIN)[0].price)
            except:
                realTimeMtdPriceDict[str(ISIN)] = currPrice
    '''
    scrollingTextDict = app.config['SCROLLING_TEXT']
    threads = []
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/69.0.3497.81 Safari/537.36',}
    scrollDict = collections.OrderedDict()
    scrollDict['S&P 500'] = []
    scrollDict['Dow 30'] = []
    scrollDict['Nasdaq'] = []
    scrollDict['10-Yr Bond'] = []
    scrollDict['EMB'] = []
    scrollDict['EEM'] = []
    scrollDict['HYG'] = []
    scrollDict['MERVAL'] = []
    scrollDict['IBOVESPA'] = []
    scrollDict['EUR'] = []
    scrollDict['GBP'] = []
    scrollDict['JPY'] = []
    scrollDict['BRL'] = []
    scrollDict['ARS'] = []
    scrollDict['MXN'] = []
    scrollDict['CNY'] = []
    scrollDict['Nikkei 225'] = []
    scrollDict['Hang Seng'] = []
    scrollDict['DAX'] = []
    scrollDict['VIX'] = []
    
    for index, url in scrollingTextDict.items(): 
        try:
            source = requests.get(url, headers=headers).text
            selector = etree.HTML(source)
            currPrice = selector.xpath('//span[@class="Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)"]')[0].text
            try:
                move = selector.xpath('//span[@class="Trsdu(0.3s) Fw(500) Pstart(10px) Fz(24px) C($dataGreen)"]')[0].text
            except:
                move = selector.xpath('//span[@class="Trsdu(0.3s) Fw(500) Pstart(10px) Fz(24px) C($dataRed)"]')[0].text
            scrollDict[index] = []
            scrollDict[index].append(currPrice)
            currValue = float(currPrice.replace(",", ""))
            moveValue = float(move.split(' ')[0].replace(",", ""))
            scrollDict[index].append(format(round(currValue + moveValue, 4), ','))
        except:
            pass
    
    print('scrollDict finished')
    
    return priceDict, fxDict, realTimeDtdPriceDict, realTimeMtdPriceDict, scrollDict

if __name__=='__main__':
    socketio.run(app, debug=True)