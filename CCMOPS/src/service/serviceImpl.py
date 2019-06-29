from flask import g, abort
from front import util, tradeInfo
from dao import db
from datetime import date, timedelta
from fractions import Fraction
from dateutil.relativedelta import *
import datetime, time, random, smtplib, shutil, os, csv, xlrd, xlwt, requests
import numpy as np
from symbol import factor
from flask import current_app
from bs4 import BeautifulSoup
from werkzeug import security
from compiler.pycodegen import EXCEPT
# new package import by jiahao_Ren
 
import operator

class Service:
    
    def tradeList(self):
        self.frontTradeList = self.bbgToFrontTradeList()
        self.tradeList = self.frontToBackTradeList(self.frontTradeList)
        
    ''' parse new FX rates into database '''
    def fxRate(self):
        file = "C:\TIMS_InputFile\FxRate\CCMFxRate.csv"
        with open(file, 'r') as fxrate:
            spamreader = csv.reader(fxrate, delimiter=',', quotechar='|')
            next(spamreader, None)
            for row in spamreader:
                tempCurrency = db.currency.Currency()
                if "\"" in row[0]:
                    tempCurrency.currType = eval(row[0])
                else:
                    tempCurrency.currType = row[0]
                if "\"" in row[1]:
                    tempCurrency.rate = float(eval(row[1]))
                else:
                    tempCurrency.rate = float(row[1])
                if "\"" in row[2]:
                    tempCurrency.tradeDate = eval(row[2])
                else:
                    tempCurrency.tradeDate = row[2]
                tempCurrency.reserve1 = 0.00
                tempCurrency.reserve2 = 0.00
                tempCurrency.reserve3 = ""
                tempCurrency.reserve4 = ""
                if len(g.dataBase.qCurrencyByDate(tempCurrency.currType, tempCurrency.tradeDate)) > 0:
                    g.dataBase.dCurrencyByTradeDate(tempCurrency.currType, tempCurrency.tradeDate)
                g.dataBase.iCurrency(tempCurrency)
        return tempCurrency
    
    ''' parse BBG trades into database '''
    def dataParsingForBBG(self):
        today = date.today()
        datestamp = today.strftime("%Y%m%d")
        newSecurityFile = "C:\TIMS_OutputFile\Files_to_Admin\RANET\CCM Trades _" + datestamp + ".csv"
        fieldsnames=['Issuer','Security Name','CUSIP','ISIN','Coupon','Maturity','Currency','Class']
        for i in self.frontTradeList:
            tempTrade = self.frontToBackTrade(i)
            tempTrade.securityType = tempTrade.tranType
            
            #operation on TradeHistory
            if tempTrade.tranType != "REPO" and tempTrade.tranType != "CREPO":
                tempSecurityList = list()
                tempFundList = list()
                tempSecurityList = g.dataBase.qSecurityBySecurityName(tempTrade)
                if len(tempSecurityList) != 0:
                    securityNo = tempSecurityList[0].securityNo
                    tempFundList = g.dataBase.qFundByCriteria(tempTrade.fundName, securityNo)
                else:
                    with open (newSecurityFile,'a') as csvfile:
                        writer = csv.DictWriter(csvfile,fieldnames=fieldsnames, lineterminator='\n')
                        if i.APP == 'FX':
                            continue
                        writer.writerow({'Issuer': i.Security,\
                             'Security Name': i.Security, \
                             'CUSIP' : i.Cusip, \
                             'ISIN': i.ISIN, \
                             'Coupon': i.Coupon, \
                             'Maturity':i.MatDt, \
                             'Currency': i.Curncy , \
                             'Class':i.APP})
                        
                if len(tempFundList) == 0:
                    tempTrade.status = "Initial"
                if len(tempFundList) != 0:
                    securityNo = tempSecurityList[0].securityNo
                    tempFundList = g.dataBase.qFundByCriteria(tempTrade.fundName, securityNo)
                    if tempFundList[0].position == "C":
                        tempTrade.status = "Initial"
                    elif tempFundList[0].position == "L":
                        if tempTrade.side == "B":
                            tempTrade.status = "Initial"
                        else:
                            if float(tempFundList[0].quantity) - float(tempTrade.quantity) >= 0:
                                tempTrade.status = "Close"
                            else:
                                tempTrade.status = "Initial"
                    else:
                        if tempTrade.side == "S":
                            tempTrade.status = "Initial"
                        else:
                            if float(tempFundList[0].quantity) - float(tempTrade.quantity) >= 0:
                                tempTrade.status = "Close"
                            else:
                                tempTrade.status = "Initial"
            
            # Operation on TradeClose Table
            self.tradeCloseProcess(tempTrade)             
            g.dataBase.iTradeHistory(tempTrade)
            
            #Operation on Security
            tempSecurity = self.tradeToSecurity(tempTrade)
            securityname = tempTrade.securityName
            templist = list()
            if tempSecurity.securityType == "REPO":
                tempSecurity.category2 = "REPO"
                g.dataBase.iSecurity(tempSecurity)
            elif tempSecurity.securityType == "CREPO":
                pass
            else:
                templist = g.dataBase.qSecurityBySecurityName(tempSecurity)
                if len(templist) == 0:
                    g.dataBase.iSecurity(tempSecurity)
                else:
                    g.dataBase.uSecurityBySecurityName(tempSecurity)
        
            #Operation on Fund
            tempFund = db.fund.Fund()
            tempSecurity = self.tradeToSecurity(tempTrade)
            tempFund.fundName = tempTrade.fundName
            tempFund.securityName = tempTrade.securityName
            if tempTrade.tranType == "REPO" or tempTrade.tranType == "CREPO":
                tempSecurityList = g.dataBase.qSecurityForRepo(tempSecurity)
                try:
                    tempsecurity2 = tempSecurityList[0]
                except:
                    print(tempTrade.securityName)
                tempFund.securityNo = tempsecurity2.securityNo
                fundresultlist = g.dataBase.qFundByCriteria(tempTrade.fundName, tempFund.securityNo)
                
                # the len(fundresultlist) == 0 meaning this is a new repo, will insert
                if len(fundresultlist) == 0:
                    tempFund.quantity = float(tempTrade.quantity)
                    if tempTrade.side == "B":
                        tempFund.position = "L"
                    else:
                        tempFund.position = "S"
                    g.dataBase.iFund(tempFund)
                # 07/1/2019 note originally there is no 'else' statement, which dose not update fund when the closing leg for repo trade entered.
                # the len(fundresultlist) != 0 means this repo was initiate before.
                else:
                    tempFund.quantity = 0
                    tempFund.position = "C"
                    g.dataBase.uFundByCriteria(tempFund)
            else:
                tempSecurityList = g.dataBase.qSecurityBySecurityName(tempSecurity)
                tempsecurity2 = tempSecurityList[0]
                tempFund.securityNo = tempsecurity2.securityNo
                fundresultlist = g.dataBase.qFundByCriteria(tempTrade.fundName, tempFund.securityNo)
                if len(fundresultlist) == 0:
                    tempFund.quantity = float(tempTrade.quantity)
                    if tempTrade.side == "B":
                        tempFund.position = "L"
                    else:
                        tempFund.position = "S"
                    g.dataBase.iFund(tempFund)
                else:
                    if fundresultlist[0].position == "L":
                        if tempTrade.side == "B":
                            tempFund.quantity = float(fundresultlist[0].quantity) + float(tempTrade.quantity)
                            tempFund.position = "L"
                        else:
                            if float(fundresultlist[0].quantity) > tempTrade.quantity:
                                tempFund.quantity = float(fundresultlist[0].quantity) - float(tempTrade.quantity)
                                tempFund.position = "L"
                            elif float(fundresultlist[0].quantity) < tempTrade.quantity:
                                tempFund.quantity = float(tempTrade.quantity) - float(fundresultlist[0].quantity)
                                tempFund.position = "S"
                            else:
                                tempFund.quantity = 0
                                tempFund.position = "C"
                    elif fundresultlist[0].position == "S":
                        if tempTrade.side == "S":
                            tempFund.quantity = float(fundresultlist[0].quantity) + float(tempTrade.quantity)
                            tempFund.position = "S"
                        else:
                            if fundresultlist[0].quantity > tempTrade.quantity:
                                tempFund.quantity = float(fundresultlist[0].quantity) - float(tempTrade.quantity)
                                tempFund.position = "S"
                            elif fundresultlist[0].quantity < tempTrade.quantity:
                                tempFund.quantity = float(tempTrade.quantity) - float(fundresultlist[0].quantity)
                                tempFund.position = "L"
                            else:
                                tempFund.quantity = 0
                                tempFund.position = "C"
                    elif fundresultlist[0].position == "C":
                        tempFund.quantity = tempTrade.quantity
                        if tempTrade.side == "B":
                            tempFund.position = "L"
                        elif tempTrade.side == "S":
                            tempFund.position = "S"
                    g.dataBase.uFundByCriteria(tempFund)
            
            #Operation on Trade
            tempSecurity = self.tradeToSecurity(tempTrade)
            if tempSecurity.securityType == "REPO" or tempSecurity.securityType == "CREPO":
                tempsecuritylist = g.dataBase.qSecurityForRepo(tempSecurity)
            else:
                tempsecuritylist = g.dataBase.qSecurityBySecurityName(tempSecurity)
            tempsecurityNo = tempsecuritylist[0].securityNo
            tempTrade.reserve4 = tempsecurityNo
            templist = g.dataBase.qFundByCriteria(tempTrade.fundName, tempsecurityNo)
            if float(templist[0].quantity) != 0.00:
                g.dataBase.iTrade(tempTrade)
            else:
                g.dataBase.dTrade(tempTrade)
    
    ''' parse FX trades into database '''
    def dataParsingForFX(self):
        for i in self.fxList:
            g.dataBase.iTradeFx(i)
    
    ''' parse new prices into database '''
    def priceUpdateFromBBG(self):
        self.autoTradeCloseForOption("PGOF")
        today = date.today()
        datestamp = today.strftime("%Y%m%d")
        file_SecUpdate = "C:\TIMS_InputFile\SecurityUpdate\Security_" + datestamp + ".xls"
        W_SecUpdate = xlrd.open_workbook(file_SecUpdate)
        SecUpdt = W_SecUpdate.sheet_by_name('Open Position')
        exceptions = ["securityNo",""]
        exceptions2 = ["REPO",""]
        exception_values = ["#N/A Field Not Applicable","#N/A","#N/A Invalid Security","#N/A N/A","#NAME?"]
        
        #update price except for REPO
        for row_idx in range(0, SecUpdt.nrows):
            if SecUpdt.cell(row_idx,0).value in exceptions:
                continue
            if SecUpdt.cell(row_idx,2).value in exceptions2:
                continue
            ph = db.priceHistory.PriceHistory()
            s = db.security.Security()
            #initiate all the values
            ph.securityNo = ""
            ph.price = 0
            ph.ai = 0
            ph.priceDate = date.today()
            s.securityNo = SecUpdt.cell(row_idx,0).value
            s.ISIN = SecUpdt.cell(row_idx,3).value
            ph.ISIN = SecUpdt.cell(row_idx,3).value
            s.bloombergId = SecUpdt.cell(row_idx,4).value
            ph.priceDate = date.today()
            if SecUpdt.cell(row_idx,5).value not in exception_values:
                ph.price = round(SecUpdt.cell(row_idx,5).value, 5)
                s.currPrice = round(SecUpdt.cell(row_idx,5).value, 5)
            if SecUpdt.cell(row_idx,6).value not in exception_values:
                try:
                    ph.ai = round(SecUpdt.cell(row_idx,6).value, 5)
                except:
                    print(ph.ISIN)
                    ph.ai = round(SecUpdt.cell(row_idx,6).value, 5)
            if SecUpdt.cell(row_idx,7).value not in exception_values:
                s.factor = round(SecUpdt.cell(row_idx,7).value, 5)
                ph.factor = round(SecUpdt.cell(row_idx,7).value, 5)
            if SecUpdt.cell(row_idx,8).value not in exception_values:
                s.spRating = SecUpdt.cell(row_idx,8).value
            if SecUpdt.cell(row_idx,9).value not in exception_values:
                s.moodyRating = SecUpdt.cell(row_idx,9).value   
            if SecUpdt.cell(row_idx,10).value not in exception_values:
                s.fitchRating  = SecUpdt.cell(row_idx,10).value
            if SecUpdt.cell(row_idx,11).value not in exception_values:
                s.comRating  = SecUpdt.cell(row_idx,11).value
            if SecUpdt.cell(row_idx,12).value not in exception_values:
                s.category1  = SecUpdt.cell(row_idx,12).value
            if SecUpdt.cell(row_idx,13).value not in exception_values:
                s.category2  = SecUpdt.cell(row_idx,13).value
            if SecUpdt.cell(row_idx,14).value not in exception_values:
                s.issueDate  = SecUpdt.cell(row_idx,14).value
            if SecUpdt.cell(row_idx,15).value not in exception_values:
                s.duration  = round(SecUpdt.cell(row_idx,15).value, 5)
            if SecUpdt.cell(row_idx,16).value not in exception_values:
                s.y  = round(SecUpdt.cell(row_idx,16).value, 5)
            elif  SecUpdt.cell(row_idx,23).value not in exception_values:
                s.y  = round(SecUpdt.cell(row_idx,23).value, 5)
            if SecUpdt.cell(row_idx,17).value not in exception_values:
                s.spread = round(SecUpdt.cell(row_idx,17).value, 5)
            if SecUpdt.cell(row_idx,18).value not in exception_values:
                s.reserve4 = SecUpdt.cell(row_idx,18).value
            if SecUpdt.cell(row_idx,19).value not in exception_values:
                s.couponFreq = SecUpdt.cell(row_idx,19).value
            if SecUpdt.cell(row_idx,20).value not in exception_values:
                s.firstCoupDt = str(SecUpdt.cell(row_idx,20).value)
            if SecUpdt.cell(row_idx,21).value not in exception_values:
                s.lastCoupDt = str(SecUpdt.cell(row_idx,21).value)
            if SecUpdt.cell(row_idx,22).value not in exception_values:
                s.liquidity = str(SecUpdt.cell(row_idx,22).value)
            try:
                s.yesPrice = g.dataBase.qPriceHistoryBeforeDate(today, s.ISIN)[0].price
            except Exception:
                pass
            
            if s.category2 != "":
                g.dataBase.uSecurityBySecurityNameForPriceUpdate(s)
            else:
                g.dataBase.uSecurityWithoutCountryForPriceUpdate(s)
            g.dataBase.iPrice(ph)
    
    def bbgToFrontTradeList(self):
        today = date.today()
        datestamp = today.strftime("%Y%m%d")
        filePath = "C:\TIMS_InputFile\TradeFile_BBG\BBGALLOC_TRADES_" + datestamp + ".csv"
        frontTradeList = list()
        
        with open(filePath, 'rU') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(spamreader, None)
            for row in spamreader:
                tempTrade = tradeInfo.Trade()
                tempTrade.APP = row[14]
                tempTrade.Status = row[0]
                tempTrade.Side = row[1]
                tempTrade.Security = row[2]            
                tempTrade.Price = float(row[3])
                tempTrade.Yield = float(row[4])
                tempTrade.Qty = float(row[5])
                if tempTrade.APP != "CALL" and tempTrade.APP != "PUT":
                    tempTrade.ISIN = row[6]
                else:
                    tempTrade.ISIN = tempTrade.Security
                tempTrade.Customer = row[7]
                tempTrade.BrkrName = row[8]
                tempTrade.Account = row[10]
                tempTrade.TradeDt = row[11]
                tempTrade.Ord_Inq = row[12]
                tempTrade.UserName = row[15]
                tempTrade.Dlr_Alias = row[16].rstrip()
                tempTrade.Brkr = row[17].rstrip()
                tempTrade.SeqNum = row[18]
                tempTrade.SetDt = row[19]
                tempcoupon = row[20].split()
                if not tempcoupon:
                    tempTrade.Coupon = 0
                elif len(tempcoupon) == 1:
                    tempTrade.Coupon = float(tempcoupon[0])
                else:
                    tempTrade.Coupon = float(tempcoupon[0]) + Fraction(tempcoupon[1])
                tempTrade.MatDt = row[21]
                tempTrade.Curncy = row[22]
                tempTrade.AccInt = float(row[23])
                tempfactor = 1
                tempTrade.Cusip = row[25]
                if tempTrade.APP == "REPO":
                    tempTrade.Cusip = g.service.fakeCusipGenerator(tempTrade.APP)
                tempTrade.Principal = float(row[26])
                tempTrade.Net = float(row[27])
                tempTrade.Rate = row[30]
                tempTrade.All_In = row[31]
                tempfactor = tempTrade.Principal/((tempTrade.Qty*1000) * (tempTrade.Price/100))
                tempTrade.Factor = round(tempfactor,10)
                if tempTrade.APP =="EQTY" or tempTrade.APP == "CALL" or tempTrade.APP == "PUT":
                    tempfactor = 1
                    if tempTrade.APP == "CALL" or tempTrade.APP == "PUT":
                        tempTrade.Cusip = self.fakeCusipGenerator(tempTrade.APP)
                if tempTrade.APP == "REPO"  :
                    tempfactor = 1
                    tempTrade.AccInt = 0
                    tempTrade.MatDt = date(2050,1,1)
                elif tempTrade.APP == "CREPO":
                    tempfactor = 1
                    tempTrade.AccInt = float(row[23])
                    tempTrade.MatDt = date(2050,1,1)       
                tempTrade.Factor = round(tempfactor,10)
                if tempTrade.APP == "EURO" or tempTrade.APP == "REPO" or tempTrade.APP == "CREPO" or tempTrade.APP == "FUT" or tempTrade.APP == "CDS":
                    tempTrade.Qty = tempTrade.Qty * 1000
                tempTrade.Custody = row[33]
                tempTrade.Remark = row[35]
                tempTrade.Bbgseq = row[18]
                frontTradeList.append(tempTrade)
        return frontTradeList
    
    def frontToBackTradeList(self, frontTradeList):
        tradeList = list()
        for i in frontTradeList:
            tradeList.append(self.frontToBackTrade(i))
        return tradeList
    
    def frontToBackTrade(self, frontTrade):
        trade = db.trade.Trade()
        trade.tranType = frontTrade.APP # Repo or Fx or Futures
        trade.CUSIP = frontTrade.Cusip
        trade.ISIN = frontTrade.ISIN
        trade.securityName = frontTrade.Security
        trade.brokerName = frontTrade.Brkr
        trade.fundName = g.fundCode[frontTrade.Account]
        trade.customerName = frontTrade.Customer
        trade.traderName = frontTrade.UserName
        trade.side = frontTrade.Side
        trade.currType = frontTrade.Curncy
        trade.price = frontTrade.Price
        trade.y = frontTrade.Yield
        trade.quantity = frontTrade.Qty
    #     trade.quantity = frontTrade.Qty*1000
        trade.principal = frontTrade.Principal
        trade.coupon = frontTrade.Coupon
        trade.accruedInt = frontTrade.AccInt
        trade.factor = frontTrade.Factor
        trade.net = frontTrade.Net
        if trade.tranType == "REPO" or trade.tranType == "CREPO":
            trade.repoRate = float(frontTrade.Rate)
            trade.price = float(frontTrade.All_In)
            trade.principal = trade.quantity * trade.price / 100
            trade.net = trade.principal +trade.accruedInt
        else:
            trade.repoRate = 0.00 # Reporate done
            trade.price = float(frontTrade.Price)#Repo Price DONE        
        trade.tradeDate = frontTrade.TradeDt
        trade.settleDate = frontTrade.SetDt
        trade.matureDate = frontTrade.MatDt
        trade.dlrAlias = frontTrade.Dlr_Alias
#         trade.principalInUSD = float(g.dataBase.qCurrencyByDate(trade.currType, trade.tradeDate)[0].rate) * float(trade.principal)
        if len(frontTrade.Remark) == 0:
            trade.remarks = ""
        else:
            trade.remarks = frontTrade.Remark
        # trade.remarks=""
        trade.reserve1 = trade.quantity
        trade.seqNo = g.service.seqGenerator(trade)
        trade.custody = frontTrade.Custody
        trade.source = "BBG"
        trade.reserve3 = str(frontTrade.Bbgseq)
        return trade
    
    def tradeToSecurity(self, trade):
        security = db.security.Security()
        security.securityName = trade.securityName
        security.securityType = trade.tranType
        security.CUSIP = trade.CUSIP
        security.ISIN = trade.ISIN
        #security.bloombergId
        tempIssuer = trade.securityName.split()
        security.issuer = tempIssuer[0]
        if trade.tranType == 'REPO':
            security.coupon = trade.repoRate
        else:
            security.coupon = trade.coupon
        if trade.coupon == 0:
            security.couponType = "L"
        else:
            security.couponType = "F"
        security.couponFreq = 2
        security.matureDate = trade.matureDate
        security.currType = trade.currType
        security.factor = float(trade.factor)
        security.yesPrice = 0.00
        security.monthPrice = 0.00
        security.currPrice = trade.price
        security.duration = 0.00
        security.spread = 0.00
        security.y = trade.y
        security.issueDate = "2017-03-22 00:00:00"
        security.category1 =""
        security.category2 = ""
        security.reserve1 = 0.00
        security.reserve2 = 0.00
        security.reserve3 = str(trade.reserve3)
        security.reserve4 = ""
        security.reserve5 = 0.00
        security.reserve6 = 0.00
        security.reserve7 = ""
        security.reserve8 = ""
        return security

    def seqGenerator(self,trade):
        random.seed(g.random)
        g.random = g.random + 1
        tempsequenceNo = str(trade.tranType) + str(trade.fundName) + trade.side + \
                         datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000000, 9999999))
        return tempsequenceNo
      
    def fakeCusipGenerator(self, tranType):
        temp = g.dataBase.qCusipNoFromConfig()
        if tranType == "REPO":
            cusipNo = g.dataBase.qCusipNoFromConfig().cusipForRepo
            temp.cusipForRepo = cusipNo + 2
            g.dataBase.uCusipInConfig(temp)
            return "_R" + str(cusipNo).zfill(7)
        elif tranType == "FUT":
            cusipNo = g.dataBase.qCusipNoFromConfig().cusipForFuture
            temp.cusipForFuture = cusipNo + 2
            g.dataBase.uCusipInConfig(temp)
            return "_U" + str(cusipNo).zfill(7)
        elif tranType == "PUT" or tranType == "CALL":
            cusipNo = g.dataBase.qCusipNoFromConfig().cusipForOption
            temp.cusipForOption = cusipNo + 2
            g.dataBase.uCusipInConfig(temp)
            return "_O" + str(cusipNo).zfill(7)
        
    def fileNotEmpty(self, source):
        today = date.today()
        datestamp = today.strftime("%Y%m%d")
        if source == "FX_RATE":
            filePath = "C:\TIMS_InputFile\FxRate\CCMFxRate_" + datestamp + ".csv"
        if source == "BBG":
            filePath = "C:\TIMS_InputFile\TradeFile_BBG\BBGALLOC_TRADES_" + datestamp + ".csv"
        elif source == "IB":
            filePath = "C:\TIMS_InputFile\TradeFile_IB\Interactive_Broker_" + datestamp + ".csv"
        elif source == "FX_TRADE":
            filePath ="C:\TIMS_InputFile\TradeFile_BBG\FX_trade_" + datestamp + ".csv"
        elif source == "PRICE":
            filePath ="C:\TIMS_InputFile\SecurityUpdate\Security_" + datestamp + ".xls"
        else:
            return False
        try:
            lines = open(filePath, "r").readlines()
        except Exception:
            return False
        if len(lines) == 0:
            return False
        else:
            return True
    
    def fileMovement(self, fileType):
        if fileType == "BBG":
            fromFilePath = r"C:\TIMS_InputFile\TradeFile_BBG\BBGALLOC_TRADES_" + time.strftime("%Y%m%d") + ".csv"
            toFilePath = r"C:\TIMS_InputFile\TradeFile_BBG\Final\BBGALLOC_TRADES_" + time.strftime("%Y%m%d%H%M%S") + ".csv"
            shutil.move(fromFilePath, toFilePath)
        
        elif fileType == "FX_TRADE":
            fromFilePath = r"C:\TIMS_InputFile\TradeFile_FX\FX_trade_" + time.strftime("%Y%m%d") + ".csv"
            toFilePath = r"C:\TIMS_InputFile\TradeFile_FX\Final\FX_trade_" + time.strftime("%Y%m%d%H%M%S") + ".csv"
            shutil.move(fromFilePath, toFilePath)
            
        elif fileType == "IB":
            fromFilePath = r"C:\TIMS_InputFile\TradeFile_IB\Interactive_Broker_" + time.strftime("%Y%m%d") + ".csv"
            toFilePath = r"C:\TIMS_InputFile\TradeFile_IB\Final\Interactive_Broker_" + time.strftime("%Y%m%d%H%M%S") + ".csv"
            shutil.move(fromFilePath, toFilePath)
    
    ''' reconcile cash with India report '''
    def getPriceFromReport(self, fundName):
        if fundName == "PGOF":
            file_temp = "C:\TIMS_InputFile\DailyReport\\pgof.xls"
        if fundName == "AGCF":
            file_temp = "C:\TIMS_InputFile\DailyReport\\agcf.xls"
        if fundName == "INC5":
            file_temp = "C:\TIMS_InputFile\DailyReport\\inc5.xls"
        tempInvest = xlrd.open_workbook(file_temp).sheet_by_name('Investments')
            
        pick  = ["Cash","Account Balances"]
        cash = 0
        for row_idx in range(0, tempInvest.nrows):
            if tempInvest.cell(row_idx,0).value in pick:
                cash += tempInvest.cell(row_idx,13).value
        pick2=["TOTAL INVESTMENTS","Foreign Currencies"]
#HELLO    WHAT IS IND
        ind=[]       
        for row_idx in range(0, tempInvest.nrows):
            if tempInvest.cell(row_idx,0).value in pick2:
                ind.append(row_idx)
        currencies=[]
#HELLO    FOREIGN CURRENCY IS ADDED THROUGH THE FOR LOOP
        for row_idx in range(ind[0], ind[1]):
            if tempInvest.cell(row_idx,1).value!='':
                a = tempInvest.cell(row_idx,1).value
                b = tempInvest.cell(row_idx,6).value
                c = tempInvest.cell(row_idx,17).value
                currencies.append({'currencyName':str(tempInvest.cell(row_idx,1).value),\
                    'Quantity':round(tempInvest.cell(row_idx,6).value,2),'CostBasis':round(tempInvest.cell(row_idx,17).value,2)})
#HELLO    US CASH IS ADDED FROM 'CASH'
        currencies.append({'currencyName':'USD','Quantity':cash,'CostBasis':cash})
        g.reportDate = (datetime.datetime(1900, 1, 1) + timedelta(days = int(tempInvest.cell(1,6).value) - 2)).date()
        return cash, currencies
    
    ''' calculate cost basis and generate costBasisPopup '''
    
    def calCostBasis(self, openPosition, fundName, tranType):
        i = 0
        j = 0
        tempCostBasis = 0
        bList = list()
        sList = list()
        trade = db.trade.Trade()
        security = db.security.Security()
        trade.ISIN = openPosition.ISIN
        trade.fundName = fundName
        trade.tranType = tranType
        security.ISIN = openPosition.ISIN
        security.securityType = tranType
        newestFactor = g.dataBase.qSecurityBySecurityName(security)[0].factor
        if tranType == "REPO":
            cusip = g.dataBase.qSecurityBySecurityNo(openPosition.securityNo)[0].CUSIP
            trade = g.dataBase.qTradeByCUSIP(cusip)[0]
            if trade.currType == 'USD':
                fx1, fx2 = 1, 1
            else:
                fx1 = float(g.dataBase.qCurrencyByDate(trade.currType, trade.tradeDate)[0].rate)
                fx2 = float(g.dataBase.qLatestCurrency(trade.currType)[0].rate)
            if trade.side == 'S':
                trade.quantity = -trade.quantity
#HELLO ??? WHY DIVEIDED BY 100                 
            tempCostBasis = float(trade.quantity) * float(trade.price) * float(trade.factor) * fx1 / 100
            tempDict = {}
            tempDate = datetime.datetime.strptime(str(trade.tradeDate), '%Y-%m-%d')
            year = str(tempDate.year)
            month = str(tempDate.month)
            day = str(tempDate.day)
            tempDict['TradeDate'] = month + '/' + day + '/' + year
            tempDict['Quantity'] = int(trade.reserve1 * (-1))
            tempDict['FxRate'] = round(fx1, 2)
            tempDict['Price'] = round(float(trade.price), 2)
            tempDict['Pnl'] = round(tempDict['Quantity'] * (float(openPosition.currPrice) * fx2 - float(trade.price) * fx1) / 100, 2)
            openPosition.costBasisPopup.append(tempDict)
        else:
            tradeList = g.dataBase.qTradeByCriteria2(trade)
            for a in tradeList:
                if a.side == "B":
                    bList.append(a)
                if a.side == "S":
                    sList.append(a)
            # combine trades within the same day
            count = 0
            while count + 1 < len(bList):
                if bList[count].tradeDate == bList[count + 1].tradeDate:
                    bList[count].reserve1 += bList[count + 1].reserve1
                    bList.pop(count + 1)
                else:
                    count += 1
            count = 0
            while count + 1 < len(sList):
                if sList[count].tradeDate == sList[count + 1].tradeDate:
                    sList[count].reserve1 += sList[count + 1].reserve1
                    sList.pop(count + 1)
                else:
                    count += 1
            countB = 0
            countS = 0
            
#HELLO ??? THIS PART IGNORES THE CLOSED POSITION             
            while countB < len(bList):
                while countS < len(sList):
                    if bList[countB].tradeDate == sList[countS].tradeDate and bList[countB].reserve1 == sList[countS].reserve1:
                        bList[countB].reserve1 = 0
                        sList[countS].reserve1 = 0
                        break
                    else:
                        countS += 1
                countB += 1
                countS = 0
                
                
                
            while i < len(bList) and j < len(sList):
                if bList[i].reserve1 > sList[j].reserve1:
                    bList[i].reserve1 = bList[i].reserve1 - sList[j].reserve1
                    sList[j].reserve1 = 0
                    j += 1
                elif bList[i].reserve1 < sList[j].reserve1:
                    sList[j].reserve1 = sList[j].reserve1 - bList[i].reserve1
                    bList[i].reserve1 = 0
                    i += 1
                else:
                    bList[i].reserve1 = 0
                    sList[j].reserve1 = 0
                    i += 1 
                    j += 1
                    
                    
                    
            if i >= len(bList):
                if tranType == "EURO":
                    for k in range(0, len(sList)):
                        if sList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(sList[k].currType, sList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(sList[k].currType)[0].rate)
                        if newestFactor > sList[k].factor:
                            tempCostBasis += \
                                (-1) * float(sList[k].reserve1) * float(sList[k].price) * float(sList[k].factor) * fx1 / 100
                        else:
                            tempCostBasis += \
                                (-1) * float(sList[k].reserve1) * float(sList[k].price) * float(newestFactor) * fx1 / 100
                        if sList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(sList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            try:
                                factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(sList[k].ISIN, sList[k].tradeDate)[0].factor)
                            except:
                                factor1 = float(sList[k].factor)
                            factor2 = float(sList[k].factor)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(sList[k].reserve1 * (-1))
                            tempDict['Price'] = round(float(sList[k].price), 2)
                            tempDict['Pnl'] = round(tempDict['Quantity'] * \
                                    (float(openPosition.currPrice) * fx2 * factor2 - float(sList[k].price) * fx1 * factor1) / 100, 2)
                            openPosition.costBasisPopup.append(tempDict)
                elif tranType == "CDS":
                    for k in range(0, len(sList)):
                        if sList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(sList[k].currType, sList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(sList[k].currType)[0].rate)
                        tempCostBasis += (-1) * float(sList[k].reserve1) * float(sList[k].price) * fx1 / 100
                        if sList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(sList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(sList[k].reserve1 * (-1))
                            tempDict['Price'] = str(round(float(sList[k].reserve2)))
                            tempDict['Pnl'] = round(tempDict['Quantity'] \
                                            * (float(openPosition.currPrice) * fx2 - float(sList[k].price) * fx1) / 100, 2)
                            openPosition.costBasisPopup.append(tempDict)
                elif tranType != "REPO":
                    for k in range(0, len(sList)):
                        if sList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(sList[k].currType, sList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(sList[k].currType)[0].rate)
                        tempCostBasis += (-1) * float(sList[k].reserve1) * float(sList[k].price) * float(sList[k].factor) * fx1
                        if sList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(sList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(sList[k].reserve1 * (-1))
                            if tranType != "FUT":
                                tempDict['Price'] = round(float(sList[k].price), 2)
                            else:
                                tempDict['Price'] = round(float(sList[k].price) / 100, 2)
                            if tranType == "FUT":
                                tempDict['Pnl'] = 0
                            else:
                                tempDict['Pnl'] = round(tempDict['Quantity'] \
                                                * (float(openPosition.currPrice) * fx2 - float(sList[k].price) * fx1), 2)
                            openPosition.costBasisPopup.append(tempDict)
            if j >= len(sList):
                if tranType == "EURO":
                    for k in range(0, len(bList)):
                        if bList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(bList[k].currType, bList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(bList[k].currType)[0].rate)
                        if newestFactor > bList[k].factor:
                            tempCostBasis += float(bList[k].reserve1) * float(bList[k].price) * float(bList[k].factor) * fx1 / 100
                        else:
                            tempCostBasis += float(bList[k].reserve1) * float(bList[k].price) * float(newestFactor) * fx1 / 100
                        if bList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(bList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            try:
                                factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(bList[k].ISIN, bList[k].tradeDate)[0].factor)
                            except:
                                factor1 = float(bList[k].factor)
                            factor2 = float(bList[k].factor)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(bList[k].reserve1)
                            tempDict['Price'] = round(float(bList[k].price), 2)
                            tempDict['Pnl'] = round(tempDict['Quantity'] \
                                * (float(openPosition.currPrice) * fx2 * factor2 - float(bList[k].price) * fx1 * factor1) / 100, 2)
                            openPosition.costBasisPopup.append(tempDict)
                elif tranType == "CDS":
                    for k in range(0, len(bList)):
                        if bList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(bList[k].currType, bList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(bList[k].currType)[0].rate)
                        tempCostBasis += float(bList[k].reserve1) * float(bList[k].price) * fx1 / 100
                        if bList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(bList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(bList[k].reserve1)
                            tempDict['Price'] = str(round(float(bList[k].reserve2)))
                            tempDict['Pnl'] = round(tempDict['Quantity'] \
                                        * (float(openPosition.currPrice) * fx2 - float(bList[k].price) * fx1) / 100, 2)
                            openPosition.costBasisPopup.append(tempDict)
                elif tranType != "REPO":
                    for k in range(0, len(bList)):
                        if bList[k].currType == 'USD':
                            fx1, fx2 = 1, 1
                        else:
                            fx1 = float(g.dataBase.qCurrencyByDate(bList[k].currType, bList[k].tradeDate)[0].rate)
                            fx2 = float(g.dataBase.qLatestCurrency(bList[k].currType)[0].rate)
                        tempCostBasis += float(bList[k].reserve1) * float(bList[k].price) * float(bList[k].factor) * fx1
                        if bList[k].reserve1 != 0:
                            tempDict = {}
                            tempDate = datetime.datetime.strptime(str(bList[k].tradeDate), '%Y-%m-%d')
                            year = str(tempDate.year)
                            month = str(tempDate.month)
                            day = str(tempDate.day)
                            tempDict['TradeDate'] = month + '/' + day + '/' + year
                            tempDict['FxRate'] = round(fx1, 2)
                            tempDict['Quantity'] = int(bList[k].reserve1)
                            if tranType != "FUT":
                                tempDict['Price'] = round(float(bList[k].price), 2)
                            else:
                                tempDict['Price'] = round(float(bList[k].price) / 100, 2)
                            if tranType == "FUT":
                                tempDict['Pnl'] = 0
                            else:
                                tempDict['Pnl'] = round(tempDict['Quantity'] \
                                        * (float(openPosition.currPrice) * fx2 - float(bList[k].price) * fx1), 2)
                            openPosition.costBasisPopup.append(tempDict)

        return tempCostBasis
    
    def summaryDetailCalculate(self, i, account):
        rate = g.dataBase.qLatestCurrency(i.currency)[0].rate
        if i.position == "S":
            i.quantity = i.quantity * (-1)
        if i.securityType == "EURO" or i.securityType == "CDS":
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            if i.securityType == "CDS":
                today = date.today().strftime("%Y-%m-%d")
                currYear = str(today)[0:4]
                today_ = datetime.datetime.strptime(today, '%Y-%m-%d')
                couponDate0_ = datetime.datetime.strptime(str(int(currYear) - 1) + '-12-20', '%Y-%m-%d')
                couponDate1_ = datetime.datetime.strptime(currYear + '-03-20', '%Y-%m-%d')
                couponDate2_ = datetime.datetime.strptime(currYear + '-06-20', '%Y-%m-%d')
                couponDate3_ = datetime.datetime.strptime(currYear + '-09-20', '%Y-%m-%d')
                couponDate4_ = datetime.datetime.strptime(currYear + '-12-20', '%Y-%m-%d')
                couponDate5_ = datetime.datetime.strptime(str(int(currYear) + 1) + '-03-20', '%Y-%m-%d')
#HELLO    ???? QUANTITTY * COUPON = ACCRUED INTEREST?
                if (today_ - couponDate1_).days > 0 and (today_ - couponDate2_).days <= 0:
                    ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate1_).days / 36000)
                elif (today_ - couponDate2_).days > 0 and (today_ - couponDate3_).days <= 0:
                    ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate2_).days / 36000)
                elif (today_ - couponDate3_).days > 0 and (today_ - couponDate4_).days <= 0:
                    ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate3_).days / 36000)
                elif (today_ - couponDate4_).days > 0 and (today_ - couponDate5_).days <= 0:
                    ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate4_).days / 36000)
                else:
                    ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate0_).days / 36000)
            if i.securityType == 'EURO':
                i.marketValue = round(float(i.quantity) * float(tempList[0].factor) \
                             * (float(tempList[0].price) + float(tempList[0].ai)) * float(rate) / 100, 2)
            elif i.securityType == 'CDS':
#HELLO ???? WHY THIS IS THE PRICE?              
                i.marketValue = round((float(i.quantity) * float(tempList[0].price) / 100 + ai) * float(rate), 2)
            i.costBasis = round(float(self.calCostBasis(i, account, i.securityType)), 2)
            i.unrzGL = round(i.quantity * i.currPrice * float(tempList[0].factor) * float(rate) / 100 - i.costBasis, 2)
        if i.securityType == "EQTY" or i.securityType == "CALL" or i.securityType == "PUT":
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            i.marketValue = round(float(i.quantity) * float(tempList[0].price) * float(rate), 2)
            i.costBasis = round(float(self.calCostBasis(i, account, i.securityType)), 2)
            i.unrzGL = round(i.marketValue - i.costBasis, 2)
        if i.securityType == "FUT":
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            i.costBasis = 0
            trade = db.trade.Trade()
            trade.ISIN = i.ISIN
            trade.fundName = account
            trade.tranType = "FUT"
            tradeList = g.dataBase.qTradeHistoryByCriteria6(i.ISIN, "FUT")
            i.marketValue = 0
            for j in tradeList:
                if j.side == "S":
                    j.reserve1 = float(j.reserve1 * (-1))
                else:
                    j.reserve1 = float(j.reserve1)
                startPrice = float(j.price) / 100
                
                i.marketValue += round(j.reserve1 * (float(tempList[0].price) - float(startPrice)) * float(rate), 2)
                
            i.unrzGL = round(i.marketValue - i.costBasis, 2)
        if i.securityType == "REPO":
            tempTrade = db.trade.Trade()
            tempTrade.ISIN = i.ISIN
            tempTrade.fundName = account
            tempTrade.tranType = "REPO"
            cusip = g.dataBase.qSecurityBySecurityNo(i.securityNo)[0].CUSIP
            tradeResult = g.dataBase.qTradeByCUSIP(cusip)[0]
            settleDate = tradeResult.settleDate
            today = date.today().strftime("%Y-%m-%d")
            settleDate_ = datetime.datetime.strptime(str(settleDate), '%Y-%m-%d')
            today_ = datetime.datetime.strptime(today, '%Y-%m-%d')
#HELLO    ???? REPO QUESTION
            i.ai = round(float(i.quantity) * float(i.currPrice) * float(tradeResult.repoRate) * float(rate) 
                         * (today_ - settleDate_).days / 36000 / 100, 2)
            i.marketValue = round(float(i.quantity) * float(i.currPrice) * float(rate) / 100 + i.ai, 2)
            i.costBasis = round(float(self.calCostBasis(i, account, "REPO")), 2)
    
    ''' main entrance to calculate summary info '''
    def summaryCalculate(self, summary, account):
        summary.cash, currencies = self.getPriceFromReport(account)
        for securityType in g.dataBase.qOpenPositionCategoryByFundName(account):
            for i in g.dataBase.qOpenPositionBySecurityType(account, securityType):
                self.summaryDetailCalculate(i, account)
                summary.marketValue += i.marketValue
                summary.costBasis += i.costBasis
                summary.gainLoss += i.unrzGL
        # CALL and PUT
        callList = g.dataBase.qOpenPositionBySecurityType(account, "CALL")
        putList = g.dataBase.qOpenPositionBySecurityType(account, "PUT")
        if len(callList) != 0:
            for i in callList:
                self.summaryDetailCalculate(i, account)
                summary.marketValue += i.marketValue
                summary.costBasis += i.costBasis
                summary.gainLoss += i.unrzGL
        if len(putList) != 0:
            for i in putList:
                self.summaryDetailCalculate(i, account)
                summary.marketValue += i.marketValue
                summary.costBasis += i.costBasis
                summary.gainLoss += i.unrzGL
        summary.cash = 0
        for i in currencies:
            if i['currencyName'] != 'USD':
                fx = round(float(g.dataBase.qLatestCurrency(i['currencyName'])[0].rate), 2)
                summary.cash += int(fx * i['Quantity'])
                summary.costBasis += int(fx * i['Quantity'])
            else:
                summary.cash += int(i['Quantity'])
                summary.costBasis += int(i['Quantity'])
        summary.accountValue = summary.marketValue + summary.cash

    def openPositionCalculate(self, i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList):
        self.calCashFlow(i, account, cashFlowList, monthlyCashFlowList)
        if i.currency != 'USD':
            rate = g.dataBase.qLatestCurrency(i.currency)[0].rate
        else:
            rate = 1
        trade = db.trade.Trade()
        trade.ISIN = i.ISIN
        trade.fundName = account
        year = date.today().strftime("%Y")
        month = date.today().strftime("%m")
        priceDate = year + "-" + month + "-" + "01"
        if i.position == "S":
            i.quantity = i.quantity * (-1)
        if i.securityType == "EURO" or i.securityType == "CDS":
            i.costBasisPopup = list()
            i.openTransPopup = list()
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            if i.yesPrice != 0:
                i.dtdPx = round((i.currPrice - i.yesPrice) / i.yesPrice * 100, 2)
            try:
                priceLastMonth = g.dataBase.qPriceHistoryByPriceDate(i.ISIN, priceDate)[0].price
                i.mtdPx = round((i.currPrice - float(priceLastMonth)) / float(priceLastMonth) * 100, 2)
            except Exception:
                i.mtdPx = 0
            if i.securityType == "EURO":
                i.ai = int(float(tempList[0].ai) * float(i.quantity) * float(tempList[0].factor) / 100)
            if i.securityType == "CDS":
                today = date.today().strftime("%Y-%m-%d")
                currYear = str(today)[0:4]
                today_ = datetime.datetime.strptime(today, '%Y-%m-%d')
                couponDate1_ = datetime.datetime.strptime(currYear + '-03-20', '%Y-%m-%d')
                couponDate2_ = datetime.datetime.strptime(currYear + '-06-20', '%Y-%m-%d')
                couponDate3_ = datetime.datetime.strptime(currYear + '-09-20', '%Y-%m-%d')
                couponDate4_ = datetime.datetime.strptime(currYear + '-12-20', '%Y-%m-%d')
                couponDate5_ = datetime.datetime.strptime(str(int(currYear) + 1) + '-03-20', '%Y-%m-%d')
                if (today_ - couponDate1_).days > 0 and (today_ - couponDate2_).days <= 0:
                    i.ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate1_).days / 36000)
                elif (today_ - couponDate2_).days > 0 and (today_ - couponDate3_).days <= 0:
                    i.ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate2_).days / 36000)
                elif (today_ - couponDate3_).days > 0 and (today_ - couponDate4_).days <= 0:
                    i.ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate3_).days / 36000)
                elif (today_ - couponDate4_).days > 0 and (today_ - couponDate5_).days <= 0:
                    i.ai = int(float(i.quantity) * float(i.coupon) * (today_ - couponDate4_).days / 36000)
                i.marketValue = int((i.quantity * float(tempList[0].price) / 100 + i.ai) * float(rate))
            if i.securityType != 'CDS':
                i.marketValue = int(float(i.quantity)*float(tempList[0].factor)*(float(tempList[0].price)+float(tempList[0].ai)) \
                                    * float(rate) / 100)
            i.costBasis = int(float(self.calCostBasis(i, account, i.securityType)))
            i.unrzGL = int(i.quantity * float(tempList[0].factor) * float(tempList[0].price) * float(rate) / 100 - i.costBasis)
            trade.tranType = i.securityType
            tradeList = g.dataBase.qTradeByCriteria2(trade)
            for j in tradeList:
                tempDict = {}
                tempDate = datetime.datetime.strptime(str(j.tradeDate), '%Y-%m-%d')
                tempDict['TradeDate'] = str(tempDate.month) + '/' + str(tempDate.day) + '/' + str(tempDate.year)
                if j.side == "S":
                    tempDict['Quantity'] = int(j.quantity * (-1))
                else:
                    tempDict['Quantity'] = int(j.quantity)
                if i.securityType =='CDS':
                    tempDict['Price'] = str(round(float(j.reserve2)))
                else:
                    tempDict['Price'] = round(float(j.price), 2)
                tradeFxRate = g.dataBase.qCurrencyByDate(j.currType, j.tradeDate)[0].rate
                tempDict['FxRate'] = round(tradeFxRate, 2)
                tempDict['Broker'] = str(j.brokerName)
                i.openTransPopup.append(tempDict)
        if i.securityType == "EQTY" or i.securityType == "CALL" or i.securityType == "PUT":
            i.costBasisPopup = list()
            i.openTransPopup = list()
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            if i.yesPrice != 0:
                i.dtdPx = round((i.currPrice - i.yesPrice) / i.yesPrice * 100, 2)
            try:
                priceLastMonth = g.dataBase.qPriceHistoryByPriceDate(i.ISIN, priceDate)[0].price
                i.mtdPx = round((i.currPrice - float(priceLastMonth)) / float(priceLastMonth) * 100, 2)
            except Exception:
                i.mtdPx = 0
            try:    
                i.marketValue = int(float(i.quantity) * float(tempList[0].price) * float(rate))
            except:
                print(i.ISIN)
            i.costBasis = int(float(self.calCostBasis(i, account, i.securityType)))
            i.unrzGL = int(i.marketValue - i.costBasis)
            trade.tranType = i.securityType
            tradeList = g.dataBase.qTradeByCriteria2(trade)
            for j in tradeList:
                tempDict = {}
                try:
                    tempDate = datetime.datetime.strptime(str(j.tradeDate), '%Y-%m-%d')
                    year = str(tempDate.year)
                    month = str(tempDate.month)
                    day = str(tempDate.day)
                    tempDict['TradeDate'] = month + '/' + day + '/' + year
                except:
                    tempDict['TradeDate'] = ''
                if j.side == "S":
                    tempDict['Quantity'] = int(j.quantity * (-1))
                else:
                    tempDict['Quantity'] = int(j.quantity)
                tempDict['Price'] = round(float(j.price), 2)
                tradeFxRate = g.dataBase.qCurrencyByDate(j.currType, j.tradeDate)[0].rate
                tempDict['FxRate'] = round(tradeFxRate, 2)
                tempDict['Broker'] = str(j.brokerName)
                i.openTransPopup.append(tempDict)
        if i.securityType == "FUT":
            i.costBasisPopup = list()
            i.openTransPopup = list()
            tempList = g.dataBase.qPriceHistoryByISIN(i.ISIN)
            if i.yesPrice != 0:
                i.dtdPx = round((i.currPrice - i.yesPrice) / i.yesPrice * 100, 2)
            try:
                priceLastMonth = g.dataBase.qPriceHistoryByPriceDate(i.ISIN, priceDate)[0].price
                i.mtdPx = round((i.currPrice - float(priceLastMonth)) / float(priceLastMonth) * 100, 2)
            except Exception:
                i.mtdPx = 0
            self.calCostBasis(i, account, "FUT")
            i.costBasis = 0
            i.ai = int(tempList[0].ai)
            trade.tranType = "FUT"
            tradeList = g.dataBase.qTradeHistoryByCriteria6(i.ISIN, "FUT")
            i.marketValue = 0
            for j in tradeList:
                tempDict = {}
                try:
                    tempDate = datetime.datetime.strptime(str(j.tradeDate), '%Y-%m-%d')
                    year = str(tempDate.year)
                    month = str(tempDate.month)
                    day = str(tempDate.day)
                    tempDict['TradeDate'] = month + '/' + day + '/' + year
                except:
                    tempDict['TradeDate'] = ''
                if j.side == "S":
                    tempDict['Quantity'] = int(j.quantity * (-1))
                    quantityNotClose = float(j.reserve1) * (-1)
                else:
                    tempDict['Quantity'] = int(j.quantity)
                    quantityNotClose = float(j.reserve1)
                tempDict['Price'] = round(float(j.price) / 100, 2)
                tradeFxRate = g.dataBase.qCurrencyByDate(j.currType, j.tradeDate)[0].rate
                tempDict['FxRate'] = round(tradeFxRate, 2)
                tempDict['Broker'] = str(j.brokerName)
                startPrice = float(j.price) / 100
                i.marketValue += int(quantityNotClose * (float(tempList[0].price) - float(startPrice)) * float(rate))
                i.openTransPopup.append(tempDict)
            i.unrzGL = int(i.marketValue - i.costBasis)
        if i.securityType == "REPO":
            i.costBasisPopup = list()
            i.openTransPopup = list()
            tempTrade = db.trade.Trade()
            tempTrade.ISIN = i.ISIN
            tempTrade.fundName = account
            tempTrade.tranType = "REPO"
            cusip = g.dataBase.qSecurityBySecurityNo(i.securityNo)[0].CUSIP
            tradeResult = g.dataBase.qTradeByCUSIP(cusip)[0]
            settleDate = tradeResult.settleDate
            today = date.today().strftime("%Y-%m-%d")
            settleDate_ = datetime.datetime.strptime(str(settleDate), '%Y-%m-%d')
            today_ = datetime.datetime.strptime(today, '%Y-%m-%d')
            i.ai = int(float(i.quantity) * float(i.currPrice) * float(tradeResult.repoRate) * float(rate) 
                         * (today_ - settleDate_).days / 36000 / 100)
            i.marketValue = int(float(i.quantity) * float(i.currPrice) * float(rate) / 100 + i.ai)
            i.costBasis = int(float(self.calCostBasis(i, account, "REPO")))
            trade.tranType = "REPO"
            tradeList = g.dataBase.qTradeByCriteria2(trade)
            for j in tradeList:
                tempDict = {}
                try:
                    tempDate = datetime.datetime.strptime(str(j.tradeDate), '%Y-%m-%d')
                    year = str(tempDate.year)
                    month = str(tempDate.month)
                    day = str(tempDate.day)
                    tempDict['TradeDate'] = month + '/' + day + '/' + year
                except:
                    tempDict['TradeDate'] = ''
                if j.side == "S":
                    tempDict['Quantity'] = int(j.quantity * (-1))
                else:
                    tempDict['Quantity'] = int(j.quantity)
                tempDict['Price'] = round(float(j.price), 2)
                tradeFxRate = g.dataBase.qCurrencyByDate(j.currType, j.tradeDate)[0].rate
                tempDict['FxRate'] = round(tradeFxRate, 2)
                tempDict['Broker'] = str(j.brokerName)
                i.openTransPopup.append(tempDict)
        i.weight = round(i.marketValue / summary.accountValue * 100, 2)
    
    def positionDetailAdd(self, positionDetailList, openPosition):
        positionDetailDict = {}
        positionDetailDict['Issuer'] = str(openPosition.issuer)
        if openPosition.securityType == "EURO" and openPosition.isDefaulted != "Y":
            positionDetailDict['Category'] = "BOND"
        elif openPosition.securityType == "EURO" and openPosition.isDefaulted == "Y":
            positionDetailDict['Category'] = "BOND (defaulted)"
        else:
            positionDetailDict['Category'] = str(openPosition.securityType)
        positionDetailDict['Coupon'] = openPosition.coupon
        try:
            tempDate = datetime.datetime.strptime(str(openPosition.matureDate), '%Y-%m-%d')
            year = str(tempDate.year)
            month = str(tempDate.month)
            day = str(tempDate.day)
            matureDate = month + '/' + day + '/' + year
            if matureDate == '1/1/2050':
                matureDate = ''
        except:
            matureDate = ''
        if str(openPosition.category) != 'REPO':
            positionDetailDict['Country'] = str(openPosition.category)
        else:
            positionDetailDict['Country'] = ''
        positionDetailDict['Maturity'] = matureDate
        positionDetailDict['Quantity'] = openPosition.quantity
        if  str(openPosition.category) == 'CDS':
            positionDetailDict['Price'] = round(openPosition.spread, 2)
        else:
            positionDetailDict['Price'] = round(openPosition.currPrice, 2)
        positionDetailDict['AI'] = openPosition.ai
        positionDetailDict['MarketValue'] = openPosition.marketValue
        positionDetailDict['Weight'] = openPosition.weight
        positionDetailDict['DTDPxChg'] = openPosition.dtdPx
        positionDetailDict['MTDPxChg'] = openPosition.mtdPx
        positionDetailDict['CostBasis'] = openPosition.costBasis
        positionDetailDict['Pnl'] = openPosition.unrzGL
        positionDetailDict['Currency'] = str(openPosition.currency)
        positionDetailDict['ISIN'] = str(openPosition.ISIN)
        positionDetailDict['Duration'] = openPosition.duration
        positionDetailDict['YTM'] = openPosition.ytm
        positionDetailDict['GSpread'] = openPosition.spread
        positionDetailDict['CbDetails'] = openPosition.costBasisPopup
        positionDetailDict['OTDetails'] = openPosition.openTransPopup
        if openPosition.ISIN == '':
            positionDetailDict['fxRate'] = 1
            positionDetailDict['factor'] = 1
        else:
            if openPosition.currency == 'USD':
                positionDetailDict['fxRate'] = 1
            else:
                positionDetailDict['fxRate'] = round(g.dataBase.qLatestCurrency(openPosition.currency)[0].rate, 2)
            if openPosition.securityType == 'EURO':
                positionDetailDict['factor'] = round(g.dataBase.qPriceHistoryByISIN(openPosition.ISIN)[0].factor, 2)
            else:
                positionDetailDict['factor'] = 1
        positionDetailList.append(positionDetailDict)
    
    ''' main entrance to calculate open positions '''
    def positionListAdd(self, positionList, countryList, summary, account, group, cashFlowList, monthlyCashFlowList):
        op = db.openPosition.OpenPosition()
        if group == "all":
            positionDetailTempList = list()
            positionTempDict = {}
            positionTempDict['categoryName'] = "ALL"
            positionTempDict['class'] = "ALL"
            for i in g.dataBase.qOpenPositionByFundName(account):
                self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                self.positionDetailAdd(positionDetailTempList, i)
            
            positionTempDict['details'] = positionDetailTempList
            positionList.append(positionTempDict)
            
        if group == "securityType":
            for securityType in g.dataBase.qOpenPositionCategoryByFundName(account):
                positionDetailTempList = list()
                positionTempDict = {}
                if securityType == "EURO":
                    positionTempDict['categoryName'] = 'BOND'
                else:
                    positionTempDict['categoryName'] = str(securityType)
                positionTempDict['class'] = str(securityType)
                for i in g.dataBase.qOpenPositionBySecurityType(account, securityType):
                    self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                    self.positionDetailAdd(positionDetailTempList, i)
                positionTempDict['details'] = positionDetailTempList
                positionList.append(positionTempDict)
            
            # CALL and PUT
            callList = g.dataBase.qOpenPositionBySecurityType(account, "CALL")
            putList = g.dataBase.qOpenPositionBySecurityType(account, "PUT")
            if len(callList) != 0 or len(putList) != 0:
                positionDetailTempList = list()
                positionTempDict = {}
                positionTempDict['categoryName'] = 'OPTION'
                positionTempDict['class'] = 'OPTION'
                if len(callList) != 0:
                    for i in callList:
                        self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                        self.positionDetailAdd(positionDetailTempList, i)
                if len(putList) != 0:
                    for i in putList:
                        self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                        self.positionDetailAdd(positionDetailTempList, i)
                positionTempDict['details'] = positionDetailTempList
                positionList.append(positionTempDict)
        
        if group == "category2":
            for country in countryList:
                if country != 'REPO':
                    positionDetailTempList = list()
                    positionTempDict = {}
                    positionTempDict['categoryName'] = str(country)
                    positionTempDict['class'] = str(country)
                    
                    
                    for i in g.dataBase.qOpenPositionByCategory(account, country):
                        self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                        self.positionDetailAdd(positionDetailTempList, i)
                    positionTempDict['details'] = positionDetailTempList
                    positionList.append(positionTempDict)
        
        if group == "currType":
            for currType in g.dataBase.qOpenPositionCurrencyByFundName(account):
                positionDetailTempList = list()
                positionTempDict = {}
                positionTempDict['categoryName'] = str(currType)
                positionTempDict['class'] = str(currType)
                for i in g.dataBase.qOpenPositionByCurrency(account, currType):
                    self.openPositionCalculate(i, positionDetailTempList, account, summary, cashFlowList, monthlyCashFlowList)
                    self.positionDetailAdd(positionDetailTempList, i)
                positionTempDict['details'] = positionDetailTempList
                positionList.append(positionTempDict)
        
        _, currencies = self.getPriceFromReport(account)
        positionDetailTempList = list()
        positionTempDict = {}
        positionTempDict['categoryName'] = 'CASH'
        positionTempDict['class'] = 'CASH'
#         op.marketValue = summary.cash
#         op.weight = round(summary.cash / summary.accountValue * 100, 2)
#         self.positionDetailAdd(positionDetailTempList, op)
        
        for i in currencies:
            positionDetailDict = {}
            positionDetailDict['Issuer'] = i['currencyName']
            positionDetailDict['Category'] = 'CASH'
            positionDetailDict['Coupon'] = 0
            positionDetailDict['Country'] = ''
            positionDetailDict['Maturity'] = ''
            positionDetailDict['Quantity'] = i['Quantity']
            if i['currencyName'] != 'USD':
                positionDetailDict['Price'] = round(float(g.dataBase.qLatestCurrency(i['currencyName'])[0].rate), 2)
            else:
                positionDetailDict['Price'] = 1
            positionDetailDict['AI'] = 0
            positionDetailDict['MarketValue'] = int(positionDetailDict['Quantity'] * positionDetailDict['Price'])
            positionDetailDict['Weight'] = round(positionDetailDict['MarketValue'] / summary.accountValue * 100, 2)
            positionDetailDict['DTDPxChg'] = 0
            positionDetailDict['MTDPxChg'] = 0
            positionDetailDict['CostBasis'] = int(i['CostBasis'])
            positionDetailDict['Pnl'] = positionDetailDict['MarketValue'] - positionDetailDict['CostBasis']
            positionDetailDict['Currency'] = i['currencyName']
            positionDetailDict['ISIN'] = i['currencyName'] + 'USD-FX'
            positionDetailDict['Duration'] = 0
            positionDetailDict['YTM'] = 0
            positionDetailDict['GSpread'] = 0
            positionDetailDict['CbDetails'] = []
            
            tempTradeFxList = []
            fxTradeList = g.dataBase.qTradeFx(i['currencyName'])
            for j in fxTradeList:
                tempDict = {}
                try:
                    tempDate = datetime.datetime.strptime(str(j.tradeDate), '%Y-%m-%d')
                    year = str(tempDate.year)
                    month = str(tempDate.month)
                    day = str(tempDate.day)
                    tempDict['TradeDate'] = month + '/' + day + '/' + year
                except:
                    tempDict['TradeDate'] = ''
                if j.side == "S":
                    tempDict['Quantity'] = int(j.quantity * (-1))
                else:
                    tempDict['Quantity'] = int(j.quantity)
                tempDict['Price'] = round(float(j.price), 2)
                tempDict['Broker'] = str(j.brokerName)
                tempTradeFxList.append(tempDict)
            positionDetailDict['OTDetails'] = tempTradeFxList
            
            positionDetailTempList.append(positionDetailDict)
        positionTempDict['details'] = positionDetailTempList
        positionList.append(positionTempDict)
    
    ''' calculate portfolio constituents by country '''
    def countryDistribution(self, countryList, country_labels_list, country_weights_list, summary, account):
        country_labels_temp_list = list()
        country_weights_temp_list = list()
        country_weights_dict = {}
        tempDict = {}
        for i in countryList:
            if i != 'None' and i != 'REPO':
                openPosition = g.dataBase.qOpenPositionByCategory(account, i)
                tempMarketValue = 0
                for j in openPosition:
                    tempList = g.dataBase.qPriceHistoryByISIN(j.ISIN)
                    rate = g.dataBase.qLatestCurrency(j.currency)[0].rate
                    if j.position == "S":
                        j.quantity = j.quantity * (-1)
                    if j.securityType == "EURO" or j.securityType == "CDS":
                        j.marketValue = round(float(j.quantity) * float(j.factor) * (float(tempList[0].price) + float(tempList[0].ai)) * float(rate) / 100, 2)
                    if j.securityType == "EQTY" or j.securityType == "CALL" or j.securityType == "PUT":
                        j.marketValue = round(float(j.quantity) * float(tempList[0].price) * float(rate), 2)
                    if j.securityType == "FUT":
                        j.marketValue = round(float(j.quantity) * (float(tempList[0].price) - float(j.yesPrice) * float(rate)), 2)
                    tempMarketValue += j.marketValue
                country_labels_temp_list.append(str(i))
                country_weights_temp_list.append(round(tempMarketValue * 100 / summary.accountValue, 2))
        
        for i in range(0, len(country_weights_temp_list)):
            tempDict[country_labels_temp_list[i]] = country_weights_temp_list[i]
        dict = sorted(tempDict.iteritems(), key=lambda d:d[1], reverse = True)
        country_weights_secondary_list = list()
        for i in dict:
            country_labels_list.append(i[0])
            country_weights_secondary_list.append(i[1])
        country_weights_dict["name"] = "Perseus"
        country_weights_dict["data"] = country_weights_secondary_list
        country_weights_list.append(country_weights_dict)
    
    def calCashFlow(self, openPosition, account, cashFlowList, monthlyCashFlowList):
        if openPosition.securityType == "EURO" or openPosition.securityType == "CDS":
            if openPosition.position == "L":
                underLying = g.dataBase.qSecurityByISIN(openPosition.ISIN)[0]
                if underLying.reserve4 == "Y":
                    pass
                elif openPosition.coupon != 0:
                    couponFreq = int(underLying.couponFreq)
                    amount = int(float(openPosition.quantity) * float(openPosition.factor) * float(openPosition.coupon) / 100 / couponFreq)
                    cashFlowDt = datetime.datetime.strptime(str(underLying.firstCoupDt),'%Y-%m-%d') + relativedelta(months=12/couponFreq)
                    startDt = datetime.datetime.strptime(date.today().strftime("%Y-%m-%d"), '%Y-%m-%d')
                    endDt = datetime.datetime.strptime(date.today().strftime("%Y-%m-%d"),'%Y-%m-%d') + relativedelta(months=12)
                    endMonth = int(endDt.strftime('%m'))
                    cashFlowMonth = int(cashFlowDt.strftime('%m'))
                    matureYear = str(underLying.matureDate)[0:4]
                    while cashFlowDt < startDt:
                        cashFlowDt = cashFlowDt + relativedelta(months=12/couponFreq)
                    while cashFlowDt >= startDt and cashFlowDt <= endDt:
                        cashFlowDict = {}
                        cashFlowDict['title'] = str(amount) + " @ " + str(underLying.issuer) + " " + matureYear + " " + str(underLying.currType)
                        cashFlowDict['start'] = cashFlowDt.strftime('%Y-%m-%d')
                        cashFlowDict['className'] = 'cf-incoming'
                        cashFlowList.append(cashFlowDict)
                        currentMonth = int(date.today().strftime("%m"))
                        cashFlowMonth = int(cashFlowDt.strftime("%m"))
                        if cashFlowMonth < currentMonth:
                            month = (cashFlowMonth + 12) - currentMonth
                        else:
                            month = cashFlowMonth - currentMonth
                        count = 0
                        for i in monthlyCashFlowList:
                            if i['name'] == str(underLying.currType):
                                monthlyCashFlowList[count]['data'][month] += int(amount)
                            else:
                                count += 1
                        cashFlowDt = cashFlowDt + relativedelta(months=12/couponFreq)
                        cashFlowMonth = int(cashFlowDt.strftime('%m'))
                else:
                    pass
            else:
                pass
        elif openPosition.securityType == "EQTY" or openPosition.securityType == "CALL" or openPosition.securityType == "PUT":
            amount = 0
        elif openPosition.securityType == "REPO":
            underLying = g.dataBase.qSecurityByISIN(openPosition.ISIN)[0]
            if underLying.reserve4 == "Y":
                amount = 0
            elif openPosition.coupon != 0:
                tempTrade = db.trade.Trade()
                tempTrade.ISIN = openPosition.ISIN
                tempTrade.fundName = account
                tempTrade.tranType = openPosition.securityType
                quantity = g.dataBase.qTradeByCriteria2(tempTrade)[0].quantity
                factor = underLying.factor
                coupon = underLying.coupon
                couponFreq = int(underLying.couponFreq)
                amount = int(float(quantity) * float(factor) * float(coupon) * (-1) / 100 / float(couponFreq))
                cashFlowDt = datetime.datetime.strptime(str(underLying.firstCoupDt),'%Y-%m-%d') + relativedelta(months=12/couponFreq)
                startDt = datetime.datetime.strptime(date.today().strftime("%Y-%m-%d"), '%Y-%m-%d')
                endDt = datetime.datetime.strptime(date.today().strftime("%Y-%m-%d"),'%Y-%m-%d') + relativedelta(months=12)
                endMonth = int(endDt.strftime('%m'))
                cashFlowMonth = int(cashFlowDt.strftime('%m'))
                matureYear = str(underLying.matureDate)[0:4]
                while cashFlowDt < startDt:
                    cashFlowDt = cashFlowDt + relativedelta(months=12/couponFreq)
                while cashFlowDt >= startDt and cashFlowDt <= endDt:
                    cashFlowDict = {}
                    cashFlowDict['title'] = str(amount) + " @ " + str(underLying.issuer) + " " + matureYear + " " + str(underLying.currType)
                    cashFlowDict['start'] = cashFlowDt.strftime('%Y-%m-%d')
                    cashFlowDict['className'] = 'cf-outgoing'
                    cashFlowList.append(cashFlowDict)
                    currentMonth = int(date.today().strftime("%m"))
                    cashFlowMonth = int(cashFlowDt.strftime("%m"))
                    if cashFlowMonth < currentMonth:
                        month = (cashFlowMonth + 12) - currentMonth
                    else:
                        month = cashFlowMonth - currentMonth
                    count = 0
                    for i in monthlyCashFlowList:
                        if i['name'] == str(underLying.currType):
                            monthlyCashFlowList[count]['data'][month] += int(amount)
                        else:
                            count += 1
                    cashFlowDt = cashFlowDt + relativedelta(months=12/couponFreq)
                    cashFlowMonth = int(cashFlowDt.strftime('%m'))
            else:
                pass
        elif openPosition.securityType == "FUT":
            amount = 0
    
    ''' calculate short-term and long-term realized G/L '''
    def calRealizedGL(self):
        tempLongTermGL = 0
        tempShortTermGL = 0
        tempCloseTradeList = g.dataBase.qTradeClose()
        for i in tempCloseTradeList:
            tradeDate1 = datetime.datetime.strptime(str(i.tradeDate1),'%Y-%m-%d')
            tradeDate2 = datetime.datetime.strptime(str(i.tradeDate2),'%Y-%m-%d')
            if tradeDate1.year == datetime.datetime.now().year:
                if (tradeDate1 - tradeDate2).days > 365:
                    if i.side1 == "B":
                        tempLongTermGL += float(i.principalInUSD2) - float(i.principalInUSD1)
                    else:
                        tempLongTermGL += float(i.principalInUSD1) - float(i.principalInUSD2)
                else:
                    if i.side1 == "B":
                        tempShortTermGL += float(i.principalInUSD2) - float(i.principalInUSD1)
                    else:
                        tempShortTermGL += float(i.principalInUSD1) - float(i.principalInUSD2)
        activeFutureList = g.dataBase.qTradeHistoryByCriteria5("FUT")
#HELLO ???? BECAUSE THE FUTURE IS MTM, EQUIVALENT TO REALIZED GAIN         
        for i in activeFutureList:
            tradeDate1 = datetime.datetime.now()
            tradeDate2 = datetime.datetime.strptime(str(i.tradeDate),'%Y-%m-%d')
            if i.currType != "USD":
                    fxRate1 = float(g.dataBase.qLatestCurrency(i.currType)[0].rate)
                    fxRate2 = float(g.dataBase.qCurrencyByDate(i.currType, tradeDate2)[0].rate)
            else:
                fxRate1 = 1
                fxRate2 = 1
            if (tradeDate1 - tradeDate2).days > 365:
                if i.side == "B":
                    tempLongTermGL += (float(g.dataBase.qPriceHistoryByISIN(i.ISIN)[0].price)*fxRate1 - float(i.price)*fxRate2/100) * float(i.reserve1)
                else:
                    tempLongTermGL += (float(i.price)*fxRate2/100 - float(g.dataBase.qPriceHistoryByISIN(i.ISIN)[0].price)*fxRate1) * float(i.reserve1)
            else:
                if i.side == "B":
                    tempShortTermGL += (float(g.dataBase.qPriceHistoryByISIN(i.ISIN)[0].price)*fxRate1 - float(i.price)*fxRate2/100) * float(i.reserve1)
                else:
                    tempShortTermGL += (float(i.price)*fxRate2/100 - float(g.dataBase.qPriceHistoryByISIN(i.ISIN)[0].price)*fxRate1) * float(i.reserve1)
            
        g.longTermGL = tempLongTermGL
        g.shortTermGL = tempShortTermGL
    
    ''' close trade '''
    def tradeCloseProcess(self, tempTrade):
        criteria = db.trade.Trade()
        criteria.ISIN = tempTrade.ISIN
        criteria.tranType = tempTrade.tranType
        criteria.fundName = tempTrade.fundName
        criteria.securityName = tempTrade.securityName
        criteria.tradeDate = tempTrade.tradeDate
        criteria.net = tempTrade.net
        criteria.quantity = tempTrade.quantity
        criteria.reserve3 = tempTrade.reserve3
        tempQuantity = float(tempTrade.quantity)
        sameDayMatchList = list()
        if tempTrade.side == "B":
            criteria.side = "S"
        if tempTrade.side == "S":
            criteria.side = "B"
        if tempTrade.tranType == "CREPO":
            criteria.tranType = "REPO"
            sameDayMatchList = g.dataBase.qTradeHistoryForCREPO(criteria)
        elif tempTrade.tranType == "REPO":
            pass
        else:
            sameDayMatchList = g.dataBase.qTradeHistoryByCriteria4(criteria)
        if len(sameDayMatchList) !=  0:
            tempTradeClose = db.tradeClose.TradeClose()
            tempTradeClose.seqNo1 = tempTrade.seqNo
            tempTradeClose.seqNo2 = sameDayMatchList[0].seqNo
            tempTradeClose.tranType = tempTrade.tranType
            tempTradeClose.CUSIP = tempTrade.CUSIP
            tempTradeClose.ISIN = tempTrade.ISIN
            tempTradeClose.securityName = tempTrade.securityName
            tempTradeClose.fundName = tempTrade.fundName
            tempTradeClose.side1 = tempTrade.side
            tempTradeClose.side2 = sameDayMatchList[0].side
            tempTradeClose.currType1 = tempTrade.currType
            tempTradeClose.currType2 = sameDayMatchList[0].currType
            tempTradeClose.price1 = tempTrade.price
            tempTradeClose.price2 = sameDayMatchList[0].price
            tempTradeClose.coupon = tempTrade.coupon
            tempTradeClose.fxRate1 = g.dataBase.qCurrencyByDate(tempTrade.currType, tempTrade.tradeDate)[0].rate
            tempTradeClose.fxRate2 = g.dataBase.qCurrencyByDate(sameDayMatchList[0].currType, sameDayMatchList[0].tradeDate)[0].rate
            if tempTradeClose.tranType == "REPO":
                tempTradeClose.repoRate = 1 #todo
            tempTradeClose.factor1 = tempTrade.factor
            tempTradeClose.factor2 = sameDayMatchList[0].factor
            tempTradeClose.commission1 = tempTrade.commission
            tempTradeClose.commission2 = sameDayMatchList[0].commission
            tempTradeClose.tradeDate1 = tempTrade.tradeDate
            tempTradeClose.tradeDate2 = sameDayMatchList[0].tradeDate
            tempTradeClose.settleDate1 = tempTrade.settleDate
            tempTradeClose.settleDate2 = sameDayMatchList[0].settleDate
            tempTradeClose.matureDate = tempTrade.matureDate
            tempTrade.reserve1 = 0
            tempTrade.reserve4 = "CLOSED"
            tempTradeClose.quantity1 = tempQuantity
            tempTradeClose.quantity2 = tempQuantity
            if tempTradeClose.factor1 >= tempTradeClose.factor2:
                tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * float(tempQuantity)  / float(tempTrade.quantity)
                tempTradeClose.principal2 = (float(sameDayMatchList[0].principal) / float(sameDayMatchList[0].factor)) * float(tempTradeClose.factor2) * float(tempQuantity) / float(sameDayMatchList[0].quantity)
            else:
                tempTradeClose.principal1 = float(tempTrade.principal) * (float(tempQuantity) * float(tempTradeClose.factor1) / float(tempTrade.quantity))
                tempTradeClose.principal2 = float(sameDayMatchList[0].principal) * (float(tempQuantity) * float(tempTradeClose.factor1) / float(sameDayMatchList[0].quantity))
            tempTradeClose.accruedInt1 = float(tempTrade.accruedInt) * (float(tempQuantity) / float(tempTrade.quantity))
            tempTradeClose.accruedInt2 = float(sameDayMatchList[0].accruedInt) * (float(tempQuantity) / float(sameDayMatchList[0].quantity))
            tempTradeClose.net1 = float(tempTrade.net) * (float(tempQuantity) / float(tempTrade.quantity))
            tempTradeClose.net2 = float(sameDayMatchList[0].net) * (float(tempQuantity) / float(sameDayMatchList[0].quantity))
            rate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
            rate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
            tempTradeClose.principalInUSD1 = tempTradeClose.principal1 * float(rate1)
            tempTradeClose.principalInUSD2 = tempTradeClose.principal2 * float(rate2)
            sameDayMatchList[0].reserve1 = 0
            sameDayMatchList[0].reserve4 = "CLOSED"
            g.dataBase.uTradeHistoryBySeqNo(sameDayMatchList[0])
            g.dataBase.iTradeClose(tempTradeClose)
        else:
            matchTradeList = list()
            if tempTrade.tranType == "CREPO":
                matchTradeList = g.dataBase.qTradeHistoryForCREPO2(criteria)
            elif tempTrade.tranType == "REPO":
                pass
            else:
                matchTradeList = g.dataBase.qTradeHistoryByCriteria2(criteria)
            if len(matchTradeList) != 0:
                for i in matchTradeList:
                    tempTradeClose = db.tradeClose.TradeClose()
                    tempTradeClose.seqNo1 = tempTrade.seqNo
                    tempTradeClose.seqNo2 = i.seqNo
                    tempTradeClose.tranType = tempTrade.tranType
                    tempTradeClose.CUSIP = tempTrade.CUSIP
                    tempTradeClose.ISIN = tempTrade.ISIN
                    tempTradeClose.securityName = tempTrade.securityName
                    tempTradeClose.fundName = tempTrade.fundName
                    tempTradeClose.side1 = tempTrade.side
                    tempTradeClose.side2 = i.side
                    tempTradeClose.currType1 = tempTrade.currType
                    tempTradeClose.currType2 = i.currType
                    tempTradeClose.price1 = tempTrade.price
                    tempTradeClose.price2 = i.price
                    tempTradeClose.coupon = tempTrade.coupon
                    tempTradeClose.fxRate1 = g.dataBase.qCurrencyByDate(tempTrade.currType, tempTrade.tradeDate)[0].rate
                    tempTradeClose.fxRate2 = g.dataBase.qCurrencyByDate(i.currType, i.tradeDate)[0].rate
                    if tempTradeClose.tranType == "REPO":
                        tempTradeClose.repoRate = 1 #todo
                    tempTradeClose.factor1 = tempTrade.factor
                    tempTradeClose.factor2 = i.factor
                    tempTradeClose.commission1 = tempTrade.commission
                    tempTradeClose.commission2 = i.commission
                    tempTradeClose.tradeDate1 = tempTrade.tradeDate
                    tempTradeClose.tradeDate2 = i.tradeDate
                    tempTradeClose.settleDate1 = tempTrade.settleDate
                    tempTradeClose.settleDate2 = i.settleDate
                    tempTradeClose.matureDate = tempTrade.matureDate
                    if float(tempQuantity) == float(i.reserve1):
                        tempTrade.reserve1 = 0
                        tempTrade.reserve4 = "CLOSED"
                        tempTradeClose.quantity1 = tempQuantity
                        tempTradeClose.quantity2 = tempQuantity
                        if tempTradeClose.factor1 >= tempTradeClose.factor2:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor2) * (float(tempQuantity) / float(i.quantity))
                        else:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(i.quantity))
                        tempTradeClose.accruedInt1 = float(tempTrade.accruedInt) * (float(tempQuantity) / float(tempTrade.quantity))
                        tempTradeClose.accruedInt2 = float(i.accruedInt) * (float(tempQuantity) / float(i.quantity))
                        tempTradeClose.net1 = float(tempTrade.net) * (float(tempQuantity) / float(tempTrade.quantity))
                        tempTradeClose.net2 = float(i.net) * (float(tempQuantity) / float(i.quantity))
                        rate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
                        rate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
                        tempTradeClose.principalInUSD1 = tempTradeClose.principal1 * float(rate1)
                        tempTradeClose.principalInUSD2 = tempTradeClose.principal2 * float(rate2)
                        i.reserve1 = 0
                        i.reserve4 = "CLOSED"
                        g.dataBase.uTradeHistoryBySeqNo(i)
                        g.dataBase.iTradeClose(tempTradeClose)
                        break
                    elif float(tempQuantity) < float(i.reserve1):
                        tempTrade.reserve1 = 0
                        tempTrade.reserve4 = "CLOSED"
                        tempTradeClose.quantity1 = tempQuantity
                        tempTradeClose.quantity2 = tempQuantity
                        if tempTradeClose.factor1 >= tempTradeClose.factor2:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor2) * (float(tempQuantity) / float(i.quantity))
                        else:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor1) * (float(tempQuantity) / float(i.quantity))
                        tempTradeClose.accruedInt1 = tempTrade.accruedInt * (float(tempQuantity) / float(tempTrade.quantity))
                        tempTradeClose.accruedInt2 = float(i.accruedInt) * (float(tempQuantity) / float(i.quantity))
                        tempTradeClose.net1 = tempTrade.net * (float(tempQuantity) / float(tempTrade.quantity))
                        tempTradeClose.net2 = float(i.net) * (float(tempQuantity) / float(i.quantity))
                        rate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
                        rate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
                        tempTradeClose.principalInUSD1 = tempTradeClose.principal1 * float(rate1)
                        tempTradeClose.principalInUSD2 = tempTradeClose.principal2 * float(rate2)
                        i.reserve1 = float(i.reserve1) - float(tempQuantity)
                        i.reserve4 = ""
                        g.dataBase.uTradeHistoryBySeqNo(i)
                        g.dataBase.iTradeClose(tempTradeClose)
                        break
                    else:
                        tempTradeClose.quantity1 = i.reserve1
                        tempTradeClose.quantity2 = i.reserve1
                        if tempTradeClose.factor1 >= tempTradeClose.factor2:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(i.reserve1) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor2) * (float(i.reserve1) / float(i.quantity))
                        else:
                            tempTradeClose.principal1 = (float(tempTrade.principal) / float(tempTrade.factor)) * float(tempTradeClose.factor1) * (float(i.reserve1) / float(tempTrade.quantity))
                            tempTradeClose.principal2 = (float(i.principal) / float(i.factor)) * float(tempTradeClose.factor1) * (float(i.reserve1) / float(i.quantity))
                        tempTradeClose.accruedInt1 = float(tempTrade.accruedInt) * (float(i.reserve1) / float(tempTrade.quantity))
                        tempTradeClose.accruedInt2 = float(i.accruedInt) * (float(i.reserve1) / float(i.quantity))
                        tempTradeClose.net1 = float(tempTrade.net) * (float(i.reserve1) / float(tempTrade.quantity))
                        tempTradeClose.net2 = float(i.net) * (float(i.reserve1) / float(i.quantity))
                        rate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
                        rate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
                        tempTradeClose.principalInUSD1 = tempTradeClose.principal1 * float(rate1)
                        tempTradeClose.principalInUSD2 = tempTradeClose.principal2 * float(rate2)
                        tempQuantity = float(tempQuantity) - float(i.reserve1)
                        tempTrade.reserve1 = tempQuantity
                        tempTrade.reserve4 = ""
                        i.reserve1 = 0
                        i.reserve4 = "CLOSED"
                        g.dataBase.uTradeHistoryBySeqNo(i)
                        g.dataBase.iTradeClose(tempTradeClose)  
        g.dataBase.uTradeFromTradeHistory()
       
    ''' reconcile available cash with India report '''
    def getAvailCashFromReport(self):
        # account order
        # AGCF, INC5, INC0, HART, PGOF, ACPT
        account_mapping ={'U1320604':"AGCF", 'U1238201':"ACPT", 'U1681581':"PGOF"}
        account_order_mapping ={'U1320604':0, 'U1238201':5, 'U1681581':4}
        
        W_liquidity = xlrd.open_workbook("C:\TIMS_InputFile\DailyReport\Liquidity Report.xls")
        liquidity = W_liquidity.sheet_by_name('Liquidity')
        
        Custody_Cash = [0,0,0,0,0,0]
        Secondary_custody = [0,0,0,0,0,0]
        ar = [0,0,0,0,0,0]
        ap = [0,0,0,0,0,0]
        fxbalance = [0,0,0,0,0,0]
        
        for row_idx in range(3, 50):
            if liquidity.cell(row_idx,0).value == "US Bank  [USBk]                         ":
                if liquidity.cell(row_idx,1).value:
                    Custody_Cash[0] += liquidity.cell(row_idx,1).value
                if liquidity.cell(row_idx,4).value:
                    Custody_Cash[3] += liquidity.cell(row_idx,4).value
                if liquidity.cell(row_idx,7).value:
                    Custody_Cash[4] += liquidity.cell(row_idx,7).value
                if liquidity.cell(row_idx,8).value:
                    Custody_Cash[5] += liquidity.cell(row_idx,8).value
                continue
            if liquidity.cell(row_idx,0).value == "State Street Custody  [STST]            ":
                Custody_Cash[1] = liquidity.cell(row_idx,2).value
                Custody_Cash[2] = liquidity.cell(row_idx,3).value
                continue
            if liquidity.cell(row_idx,0).value == "The Bank of Nova Scotia  [BNS]  476..311":
                Custody_Cash[1] = Custody_Cash[1]+liquidity.cell(row_idx,2).value
                continue
            if liquidity.cell(row_idx,0).value == "The Bank of Nova Scotia  [BNS]  476..515":
                Custody_Cash[2] = Custody_Cash[2]+liquidity.cell(row_idx,3).value
                continue
            if liquidity.cell(row_idx,0).value == "Accounts Receivable":
                ar[0] = liquidity.cell(row_idx,1).value
                ar[1] = liquidity.cell(row_idx,2).value
                ar[2] = liquidity.cell(row_idx,3).value
                ar[3] = liquidity.cell(row_idx,4).value
                ar[4] = liquidity.cell(row_idx,7).value
                ar[5] = liquidity.cell(row_idx,8).value
                continue
            if liquidity.cell(row_idx,0).value == "Accounts Payable":
                ap[0] = liquidity.cell(row_idx,1).value
                ap[1] = liquidity.cell(row_idx,2).value
                ap[2] = liquidity.cell(row_idx,3).value
                ap[3] = liquidity.cell(row_idx,4).value
                ap[4] = liquidity.cell(row_idx,7).value
                ap[5] = liquidity.cell(row_idx,8).value
                continue
            if liquidity.cell(row_idx,0).value == "Cash Equivalents":
                if liquidity.cell(row_idx,1).value:
                    Custody_Cash[0] += liquidity.cell(row_idx,1).value
                if liquidity.cell(row_idx,4).value:
                    Custody_Cash[3] += liquidity.cell(row_idx,4).value
                if liquidity.cell(row_idx,7).value:
                    Custody_Cash[4] += liquidity.cell(row_idx,7).value
                if liquidity.cell(row_idx,8).value:
                    Custody_Cash[5] += liquidity.cell(row_idx,8).value
                continue
            if liquidity.cell(row_idx,0).value == "Foreign Currency":
                fxbalance[0] = liquidity.cell(row_idx,1).value
                fxbalance[1] = liquidity.cell(row_idx,2).value
                fxbalance[2] = liquidity.cell(row_idx,3).value
                fxbalance[3] = liquidity.cell(row_idx,4).value
                fxbalance[4] = liquidity.cell(row_idx,7).value
                fxbalance[5] = liquidity.cell(row_idx,8).value
                continue
        
        W_ibmargin = xlrd.open_workbook("C:\TIMS_InputFile\DailyReport\IBmargins.xls")
        sheetname= W_ibmargin.sheet_names()
        ibmargin = W_ibmargin.sheet_by_name(sheetname[0])
        
        rowindex=[]
        accounts=[]
        for i in range(ibmargin.nrows):
            if ibmargin.cell(i,0).value=="BOF":
                rowindex.append(i)
                accounts.append(ibmargin.cell(i,1).value)
        rowindex.append(ibmargin.nrows-1)     
        
        for j in range(len(accounts)):
            try:
                x = account_mapping[accounts[j]]
            except KeyError:
                continue
            temp1 = 0
            temp2 = 0
            for k in range(rowindex[j+1]-rowindex[j]):
                if ibmargin.cell(k+rowindex[j],2).value =="CashValue":
                    temp1=ibmargin.cell(k+rowindex[j],5).value
                if ibmargin.cell(k+rowindex[j],2).value =="AvailableFunds":
                    temp2=ibmargin.cell(k+rowindex[j],5).value
            Secondary_custody[account_order_mapping[accounts[j]]]=min(temp1,temp2)
                
        #total_liquidity = np.array(Custody_Cash)+np.array(Secondary_custody)+np.array(ar)+np.array(ap)+np.array(fxbalance)        
        total_liquidity = np.array(Custody_Cash)+np.array(Secondary_custody)+np.array(ar)+np.array(ap)       
        liquidity_list={
                "Andromeda":{
                        "USBK":int(Custody_Cash[0])+int(ar[0])+int(ap[0]),
                        "ITBK":Secondary_custody[0],
                        "FX":fxbalance[0],
                        "Total":total_liquidity[0]
                        },
                "Perseus":{
                        "USBK":int(Custody_Cash[4])+int(ar[4])+int(ap[4]),
                        "ITBK":int(Secondary_custody[4]),
                        "FX":int(fxbalance[4]),
                        "Total":int(total_liquidity[4])
                        },
                "Hartz":{
                        "USBK":Custody_Cash[3],
                        "ITBK":Secondary_custody[3],
                        "FX":fxbalance[3],
                        "Total":total_liquidity[3]
                        },
                "Baldr Draco A":{
                        "SSBK":Custody_Cash[1],
                        "BKNS":Secondary_custody[1],
                        "FX":fxbalance[1],
                        "Total":total_liquidity[1]
                        },
                "Baldr Draco B":{
                        "SSBK":Custody_Cash[2],
                        "BKNS":Secondary_custody[2],
                        "FX":fxbalance[2],
                        "Total":total_liquidity[2]
                        },
                "Aspen Creek":{
                        "USBK":int(Custody_Cash[5])+int(ar[5])+int(ap[5]),
                        "ITBK":Secondary_custody[5],
                        "FX":fxbalance[5],
                        "Total":total_liquidity[5]
                        }    
            }
        return liquidity_list
    
    ''' generate realized G/L report '''
    def realizedGLDetails(self, year, month):
        
        g.queryRealizedGL = 0
        realizedGLList = list()
        
        bondDict = {}
        equityDict = {}
        futureDict = {}
        repoDict = {}
        optionDict = {}
        cdsDict = {}
        
        bondDict['categoryName'] = "BOND"
        bondDict['class'] = "bond"
        bondDict['details'] = []
        equityDict['categoryName'] = "EQUITY"
        equityDict['class'] = "equity"
        equityDict['details'] = []
        futureDict['categoryName'] = "FUTURE"
        futureDict['class'] = "future"
        futureDict['details'] = []
        repoDict['categoryName'] = "REPO"
        repoDict['class'] = "repo"
        repoDict['details'] = []
        optionDict['categoryName'] = "OPTION"
        optionDict['class'] = "option"
        optionDict['details'] = []
        cdsDict['categoryName'] = "CDS"
        cdsDict['class'] = "cds"
        cdsDict['details'] = []
        
        for i in g.dataBase.qISINFromTradeClose():
            tradeCloseListWithoutREPO = g.dataBase.qTradeCloseByISIN(i)
            if len(tradeCloseListWithoutREPO) > 0:
                tempRealizedGL = db.realizedGL.RealizedGL()
                tempDict = {}
                realizedDetailList = []
                status = 0
                for j in tradeCloseListWithoutREPO:
                    s = db.security.Security()
                    s.ISIN = i
                    s.securityType = j.tranType
                    tradeDate1 = datetime.datetime.strptime(str(j.tradeDate1),'%Y-%m-%d')
                    tradeDate2 = datetime.datetime.strptime(str(j.tradeDate2),'%Y-%m-%d')
                    if tradeDate1.year == int(year):
                        if month == "0" or tradeDate1.month == int(month):
                            status = 1
                            tempRealizedGL.ISIN = str(j.ISIN)
                            tempRealizedGL.securityName = str(j.securityName)
                            tempRealizedGL.securityType = s.securityType
                            tempRealizedGL.country = str(g.dataBase.qSecurityBySecurityName(s)[0].category2)
                            realizedDetailDict = {}
                            realizedDetailDict['initialDate'] = str(tradeDate2.month) + '/' + str(tradeDate2.day) + '/' + str(tradeDate2.year)
                            realizedDetailDict['closeDate'] = str(tradeDate1.month) + '/' + str(tradeDate1.day) + '/' + str(tradeDate1.year)
                            realizedDetailDict['initialPrice'] = float(j.price2)
                            realizedDetailDict['closePrice'] = float(j.price1)
                            if j.side1 == "B":
                                tempRealizedGL.cost += float(j.principalInUSD1)
                                tempRealizedGL.proceeds += float(j.principalInUSD2)
                                tempRealizedGL.intExpense += float(j.accruedInt1) * float(j.fxRate1)
                                tempRealizedGL.intRevenue += float(j.accruedInt2) * float(j.fxRate2)
                                realizedDetailDict['quantity'] = float(j.quantity1) * (-1)
                                realizedDetailDict['pnl'] = round(float(j.principalInUSD2) - float(j.principalInUSD1), 2)
                            else:
                                tempRealizedGL.cost += float(j.principalInUSD2)
                                tempRealizedGL.proceeds += float(j.principalInUSD1)
                                tempRealizedGL.intExpense += float(j.accruedInt2) * float(j.fxRate2)
                                tempRealizedGL.intRevenue += float(j.accruedInt1) * float(j.fxRate1)
                                realizedDetailDict['quantity'] = float(j.quantity1)
                                realizedDetailDict['pnl'] = round(float(j.principalInUSD1) - float(j.principalInUSD2), 2)
                            realizedDetailList.append(realizedDetailDict)
                            if (tradeDate1 - tradeDate2).days > 365:
                                if tempRealizedGL.securityType != 'FUT':
                                    if j.side1 == "B":
                                        tempRealizedGL.ltGain += float(j.principalInUSD2) - float(j.principalInUSD1)
                                    else:
                                        tempRealizedGL.ltGain += float(j.principalInUSD1) - float(j.principalInUSD2)
                                else:
                                    if j.side1 == "B":
                                        tempRealizedGL.ltGain += (float(j.principalInUSD2) - float(j.principalInUSD1)) * 0.6
                                        tempRealizedGL.stGain += (float(j.principalInUSD2) - float(j.principalInUSD1)) * 0.4
                                    else:
                                        tempRealizedGL.ltGain += (float(j.principalInUSD1) - float(j.principalInUSD2)) * 0.6
                                        tempRealizedGL.stGain += (float(j.principalInUSD1) - float(j.principalInUSD2)) * 0.4
                            else:
                                if tempRealizedGL.securityType != 'FUT':
                                    if j.side1 == "B":
                                        tempRealizedGL.stGain += float(j.principalInUSD2) - float(j.principalInUSD1)
                                    else:
                                        tempRealizedGL.stGain += float(j.principalInUSD1) - float(j.principalInUSD2)
                                else:
                                    if j.side1 == "B":
                                        tempRealizedGL.ltGain += (float(j.principalInUSD2) - float(j.principalInUSD1)) * 0.6
                                        tempRealizedGL.stGain += (float(j.principalInUSD2) - float(j.principalInUSD1)) * 0.4
                                        
                                    else:
                                        tempRealizedGL.ltGain += (float(j.principalInUSD1) - float(j.principalInUSD2)) * 0.6
                                        tempRealizedGL.stGain += (float(j.principalInUSD1) - float(j.principalInUSD2)) * 0.4
                            tempDict['Coupon'] = float(j.coupon)
                            tempDict['Maturity'] = str(j.matureDate)
                            tempDict['Currency'] = str(j.currType1)
                if status == 1:
                    tempRealizedGL.totalInUSD = tempRealizedGL.ltGain + tempRealizedGL.stGain
                    g.queryRealizedGL += tempRealizedGL.totalInUSD
                    tempDict['realizedDetails'] = realizedDetailList
                    tempDict['SecurityName'] = tempRealizedGL.securityName
                    tempDict['Country'] = tempRealizedGL.country
                    tempDict['Cost'] = tempRealizedGL.cost
                    tempDict['Proceeds'] = tempRealizedGL.proceeds
                    tempDict['stgainloss'] = tempRealizedGL.stGain
                    tempDict['ltgainloss'] = tempRealizedGL.ltGain
                    tempDict['intexp'] = tempRealizedGL.intExpense
                    tempDict['intrev'] = tempRealizedGL.intRevenue
                    tempDict['totalrlzusd'] = tempRealizedGL.totalInUSD
                    tempDict['ISIN'] = tempRealizedGL.ISIN
                    tempDict['ordinaryIncome'] = 0
                    tempDict['totalrlz'] = 0
                    if tempRealizedGL.securityType == "EURO":
                        bondDict['details'].append(tempDict)
                    if tempRealizedGL.securityType == "EQTY":
                        equityDict['details'].append(tempDict)
                    if tempRealizedGL.securityType == "FUT":
                        futureDict['details'].append(tempDict)
                    if tempRealizedGL.securityType == "CALL" or tempRealizedGL.securityType == "PUT":
                        optionDict['details'].append(tempDict)
                    if tempRealizedGL.securityType == "CDS":
                        cdsDict['details'].append(tempDict) 
                else:
                    pass
            
            tradeCloseListForREPO = g.dataBase.qTradeCloseByISIN2(i)
            if len(tradeCloseListForREPO) > 0:
                tempRealizedGL = db.realizedGL.RealizedGL()
                tempDict2 = {}
                realizedDetailList = []
                status = 0
                for j in tradeCloseListForREPO:
                    s = db.security.Security()
                    s.ISIN = i
                    s.securityType = "REPO"
                    tradeDate1 = datetime.datetime.strptime(str(j.tradeDate1),'%Y-%m-%d')
                    tradeDate2 = datetime.datetime.strptime(str(j.tradeDate2),'%Y-%m-%d')
                    if tradeDate1.year == int(year):
                        if month == "0" or tradeDate1.month == int(month):
                            status = 1
                            tempRealizedGL.ISIN = str(j.ISIN)
                            tempRealizedGL.securityName = str(j.securityName)
                            tempRealizedGL.securityType = s.securityType
                            tempRealizedGL.country = str(g.dataBase.qSecurityBySecurityName(s)[0].category2)
                            realizedDetailDict = {}
                            realizedDetailDict['initialDate'] = str(tradeDate2.month) + '/' + str(tradeDate2.day) + '/' + str(tradeDate2.year)
                            realizedDetailDict['closeDate'] = str(tradeDate1.month) + '/' + str(tradeDate1.day) + '/' + str(tradeDate1.year)
                            realizedDetailDict['initialPrice'] = float(j.price2)
                            realizedDetailDict['closePrice'] = float(j.price1)
                            if j.side1 == "B":
                                tempRealizedGL.cost += float(j.principalInUSD1)
                                tempRealizedGL.proceeds += float(j.principalInUSD2)
                                tempRealizedGL.intExpense += abs(float(j.accruedInt2)) * float(j.fxRate2)
                                tempRealizedGL.intRevenue += abs(float(j.accruedInt1)) * float(j.fxRate1)
                                realizedDetailDict['quantity'] = float(j.quantity1) * (-1)
                                realizedDetailDict['pnl'] = round(float(j.principalInUSD2) - float(j.principalInUSD1), 2)
                            else:
                                tempRealizedGL.cost += float(j.principalInUSD2)
                                tempRealizedGL.proceeds += float(j.principalInUSD1)
                                tempRealizedGL.intExpense += abs(float(j.accruedInt1)) * float(j.fxRate1)
                                tempRealizedGL.intRevenue += abs(float(j.accruedInt2)) * float(j.fxRate2)
                                realizedDetailDict['quantity'] = float(j.quantity1)
                                realizedDetailDict['pnl'] = round(float(j.principalInUSD1) - float(j.principalInUSD2), 2)
                            realizedDetailList.append(realizedDetailDict)
                            if (tradeDate1 - tradeDate2).days > 365:
                                if j.side1 == "B":
                                    tempRealizedGL.ltGain += float(j.principalInUSD2) - float(j.principalInUSD1)
                                else:
                                    tempRealizedGL.ltGain += float(j.principalInUSD1) - float(j.principalInUSD2)
                            else:
                                if j.side1 == "B":
                                    tempRealizedGL.stGain += float(j.principalInUSD2) - float(j.principalInUSD1)
                                else:
                                    tempRealizedGL.stGain += float(j.principalInUSD1) - float(j.principalInUSD2)
                            tempDict2['Coupon'] = float(j.coupon)
                            tempDict2['Maturity'] = str(j.matureDate)
                            tempDict2['Currency'] = str(j.currType1)
                if status == 1:
                    tempRealizedGL.totalInUSD = tempRealizedGL.ltGain + tempRealizedGL.stGain
                    g.queryRealizedGL += tempRealizedGL.totalInUSD
                    tempDict2['realizedDetails'] = realizedDetailList
                    tempDict2['SecurityName'] = tempRealizedGL.securityName
                    tempDict2['Country'] = tempRealizedGL.country
                    tempDict2['Cost'] = tempRealizedGL.cost
                    tempDict2['Proceeds'] = tempRealizedGL.proceeds
                    tempDict2['stgainloss'] = tempRealizedGL.stGain
                    tempDict2['ltgainloss'] = tempRealizedGL.ltGain
                    tempDict2['intexp'] = tempRealizedGL.intExpense
                    tempDict2['intrev'] = tempRealizedGL.intRevenue
                    tempDict2['totalrlzusd'] = tempRealizedGL.totalInUSD
                    tempDict2['ISIN'] = tempRealizedGL.ISIN
                    tempDict2['ordinaryIncome'] = 0
                    tempDict2['totalrlz'] = 0
                    repoDict['details'].append(tempDict2)   
                else:
                    pass
                       
        for j in g.dataBase.qISINFromTradeHistoryForFut():
            tempRealizedGL = db.realizedGL.RealizedGL()
            tempDict3 = {}
            status = 0
            for i in g.dataBase.qTradeHistoryByISIN(j, "FUT"):
                s = db.security.Security()
                s.ISIN = i.ISIN
                s.securityType = i.tranType
                tradeDate1 = datetime.datetime.now()
                tradeDate2 = datetime.datetime.strptime(str(i.tradeDate),'%Y-%m-%d')
                matureDate = datetime.datetime.strptime(str(i.matureDate),'%Y-%m-%d')
                if matureDate.year == int(year):
                    if month == "0" or matureDate.month == int(month):
                        status = 1
                        tempQueryDate = str(tradeDate1.year) + "-01-01"
                        tempRealizedGL.ISIN = str(i.ISIN)
                        tempRealizedGL.securityName = str(i.securityName)
                        tempRealizedGL.securityType = str(i.tranType)
                        tempRealizedGL.country = str(g.dataBase.qSecurityBySecurityName(s)[0].category2)
                        try:
                            startPrice = g.dataBase.qPriceHistoryBeforeDate(tempQueryDate, i.ISIN)[0].price
                        except Exception:
                            startPrice = g.dataBase.qTradeHistoryByDate(i.ISIN, i.tranType, i.tradeDate)[0].price / 100
                        currPrice = float(g.dataBase.qPriceHistoryByISIN(i.ISIN)[0].price)
                        if i.currType != "USD":
                            startDate = g.dataBase.qPriceHistoryBeforeDate(tempQueryDate, i.ISIN)[0].priceDate
                            fxRate1 = float(g.dataBase.qLatestCurrency(i.currType)[0].rate)
                            fxRate2 = float(g.dataBase.qCurrencyByDate(i.currType, startDate)[0].rate)
                        else:
                            fxRate1 = 1
                            fxRate2 = 1
                        if (tradeDate1 - tradeDate2).days > 365:
                            if i.side == "B":
                                tempRealizedGL.proceeds += currPrice * float(i.reserve1) * fxRate1
                                tempRealizedGL.cost += float(startPrice) * float(i.reserve1) * fxRate2
                                tempRealizedGL.ltGain += ((currPrice*fxRate1-float(startPrice)*fxRate2)*float(i.reserve1)) * 0.6
                                tempRealizedGL.stGain += ((currPrice*fxRate1-float(startPrice)*fxRate2)*float(i.reserve1)) * 0.4
                            else:
                                tempRealizedGL.cost += currPrice * float(i.reserve1) * fxRate1
                                tempRealizedGL.proceeds += float(startPrice) * float(i.reserve1) * fxRate2
                                tempRealizedGL.ltGain += ((float(startPrice)*fxRate2-currPrice*fxRate1)*float(i.reserve1)) * 0.6
                                tempRealizedGL.stGain += ((float(startPrice)*fxRate2-currPrice*fxRate1)*float(i.reserve1)) * 0.4
                        else:
                            if i.side == "B":
                                tempRealizedGL.proceeds += currPrice * float(i.reserve1) * fxRate1
                                tempRealizedGL.cost += float(startPrice) * float(i.reserve1) * fxRate2
                                tempRealizedGL.stGain += ((currPrice*fxRate1-float(startPrice)*fxRate2)*float(i.reserve1)) * 0.4
                                tempRealizedGL.ltGain += ((currPrice*fxRate1-float(startPrice)*fxRate2)*float(i.reserve1)) * 0.6
                            else:
                                tempRealizedGL.cost += currPrice * float(i.reserve1) * fxRate1
                                tempRealizedGL.proceeds += float(startPrice) * float(i.reserve1) * fxRate2
                                tempRealizedGL.stGain += ((float(startPrice)*fxRate2-currPrice*fxRate1)*float(i.reserve1)) * 0.4
                                tempRealizedGL.ltGain += ((float(startPrice)*fxRate2-currPrice*fxRate1)*float(i.reserve1)) * 0.6
                        tempDict3['Coupon'] = float(i.coupon)
                        tempDict3['Maturity'] = str(i.matureDate)
                        tempDict3['Currency'] = str(i.currType)
            if status == 1:
                tempRealizedGL.totalInUSD = tempRealizedGL.ltGain + tempRealizedGL.stGain
                g.queryRealizedGL += tempRealizedGL.totalInUSD
                tempDict3['SecurityName'] = tempRealizedGL.securityName
                tempDict3['Country'] = tempRealizedGL.country
                tempDict3['Cost'] = tempRealizedGL.cost
                tempDict3['Proceeds'] = tempRealizedGL.proceeds
                tempDict3['stgainloss'] = tempRealizedGL.stGain
                tempDict3['ltgainloss'] = tempRealizedGL.ltGain
                tempDict3['intexp'] = tempRealizedGL.intExpense
                tempDict3['intrev'] = tempRealizedGL.intRevenue
                tempDict3['totalrlzusd'] = tempRealizedGL.totalInUSD
                tempDict3['ISIN'] = tempRealizedGL.ISIN
                tempDict3['ordinaryIncome'] = 0
                tempDict3['totalrlz'] = 0
                futureDict['details'].append(tempDict3)
        
        if len(bondDict['details']) > 0:
            realizedGLList.append(bondDict)
        if len(equityDict['details']) > 0:
            realizedGLList.append(equityDict)
        if len(futureDict['details']) > 0:
            realizedGLList.append(futureDict)
        if len(repoDict['details']) > 0:
            realizedGLList.append(repoDict)
        if len(optionDict['details']) > 0:
            realizedGLList.append(optionDict)
        if len(cdsDict['details']) > 0:
            realizedGLList.append(cdsDict)
        
        return realizedGLList
    
    ''' generate investor report '''
    def shareholderDetails(self, account, investorName, year, month):
        
        if year != "2016":
            yearStartDate = datetime.datetime(int(year), 1, 1)
        else:
            yearStartDate = datetime.datetime(int(year), 5, 2)
        queryStartDate = datetime.datetime(int(year), int(month), 1)
        queryEndDate = queryStartDate + relativedelta(months = 1)
        shareholders = db.frontInvestPNL.FrontInvestPNL()
        
        currShares = float(g.dataBase.qTotalSharesFromInvestHistory(investorName, account, queryEndDate)[0])
        sharesYearStart = float(g.dataBase.qTotalSharesFromInvestHistory(investorName, account, yearStartDate)[0])
        
        navABegin = float(g.dataBase.qAccountHistoryBeforeDate(account, queryEndDate)[1].navA)
        navAEnd = float(g.dataBase.qAccountHistoryBeforeDate(account, queryEndDate)[0].navA)
        navAYearStart = float(g.dataBase.qAccountHistoryBeforeDate(account, yearStartDate)[0].navA)
        
        investHistory, documentList = g.dataBase.qInvestHistoryByInvestorName(investorName, account, queryStartDate, queryEndDate)
        investHistoryYTD, documentList = g.dataBase.qInvestHistoryByInvestorName(investorName, account, yearStartDate, queryEndDate)
        if len(investHistory) != 0:
            for i in investHistory:
                if i.side == "subscription":
                    shareholders.subscriptionRange += int(i.amount)
                else:
                    shareholders.redemptionRange += int(i.amount)
        if len(investHistoryYTD) != 0:
            for i in investHistoryYTD:
                if i.side == "subscription":
                    shareholders.subscriptionYear += int(i.amount)
                else:
                    shareholders.redemptionYear += int(i.amount)
        shareholders.investorName = investorName
        shareholders.fundName = account
        shareholders.accountValueStartDt = int(navABegin * currShares)
        shareholders.accountValueEndDt = int(navAEnd * currShares)
        shareholders.accountValueYearStart = int(navAYearStart * sharesYearStart)
        shareholders.deltaAccountValue = shareholders.accountValueEndDt - shareholders.accountValueStartDt \
                                            - shareholders.subscriptionRange + shareholders.redemptionRange
        shareholders.deltaAccountValueYTD = shareholders.accountValueEndDt - shareholders.accountValueYearStart \
                                            - shareholders.subscriptionYear + shareholders.redemptionYear
        shareholders.currReturn = round((navAEnd / navABegin - 1) * 100, 2)
        shareholders.ytdReturn = round((navAEnd / navAYearStart - 1) * 100, 2)
        
        return shareholders
    
    ''' draw investor chart '''
    def shareholdersChart(self, account, investorName):
        investHistory = g.dataBase.qInvestHistoryByInvestorName2(investorName, account)
        shares = investHistory[0].share
        startDate = investHistory[0].tradeDate
        valueList = list()
        accountValueList = list()
        colorList = list()
        categoryList = list()
        valueDict = {}
        for i in range(1, len(investHistory)):
            endDate = investHistory[i].tradeDate
            accountHistory = g.dataBase.qAccountHistoryWithinDateRange(account, startDate, endDate)
            for j in accountHistory:
                accountValueList.append(int(float(j.navA) * float(shares)))
                categoryList.append(str(j.tradeDate)[0:7])
                if len(accountValueList) == 1:
                    colorList.append('#1aa508')
                elif accountValueList[-1] < accountValueList[-2]:
                    colorList.append('#bc1a1a')
                else:
                    colorList.append('#1aa508')
                    
            if investHistory[i].side == "subscription":
                shares += investHistory[i].share
            else:
                shares -= investHistory[i].share
            startDate = endDate
        accountHistory = g.dataBase.qAccountHistoryAfterDate(account, startDate)
        for i in accountHistory:
            accountValueList.append(int(float(i.navA) * float(shares)))
            categoryList.append(str(i.tradeDate)[0:7])
            if len(accountValueList) == 1:
                colorList.append('#1aa508')
            elif accountValueList[-1] < accountValueList[-2]:
                colorList.append('#bc1a1a')
            else:
                colorList.append('#1aa508')
        if investorName == 'Shahriar':
            investorName = 'Investor S'
        if investorName == 'Green':
            investorName = 'Trust G'
        if investorName == 'Blue':
            investorName = 'Trust B'
        valueDict["name"] = investorName
        valueDict["data"] = accountValueList
        valueList.append(valueDict)
        return valueList, colorList, categoryList
    
    ''' close options when mature '''
    def autoTradeCloseForOption(self, fundName):
        callList = g.dataBase.qOpenPositionBySecurityType(fundName, "CALL")
        putList = g.dataBase.qOpenPositionBySecurityType(fundName, "PUT")
        for i in callList:
            matureDate = datetime.datetime.strptime(str(i.matureDate),'%Y-%m-%d')
            if datetime.datetime.now() >= matureDate:
                tempTradeList = g.dataBase.qTradeHistoryByISIN(i.ISIN, i.securityType)
                for tempTrade in tempTradeList:
                    tempTradeClose = db.tradeClose.TradeClose()
                    tempTradeClose.seqNo1 = tempTrade.seqNo
                    tempTradeClose.seqNo2 = tempTrade.seqNo
                    tempTradeClose.tranType = tempTrade.tranType
                    tempTradeClose.CUSIP = tempTrade.CUSIP
                    tempTradeClose.ISIN = tempTrade.ISIN
                    tempTradeClose.securityName = tempTrade.securityName
                    tempTradeClose.fundName = tempTrade.fundName
                    tempTradeClose.side2 = tempTrade.side
                    if str(tempTradeClose.side2) ==  "B":
                        tempTradeClose.side1 = "S"
                    else:
                        tempTradeClose.side1 = "B"
                    tempTradeClose.currType1 = tempTrade.currType
                    tempTradeClose.currType2 = tempTrade.currType
                    tempTradeClose.price1 = 0
                    tempTradeClose.price2 = tempTrade.price
                    tempTradeClose.quantity1 = tempTrade.reserve1
                    tempTradeClose.quantity2 = tempTrade.reserve1
                    tempTradeClose.principal1 = 0
                    tempTradeClose.principal2 = tempTrade.principal
                    tempTradeClose.coupon = tempTrade.coupon
                    tempTradeClose.accruedInt1 = tempTrade.accruedInt
                    tempTradeClose.accruedInt2 = tempTrade.accruedInt
                    tempTradeClose.repoRate = tempTrade.repoRate
                    tempTradeClose.factor1 = tempTrade.factor
                    tempTradeClose.factor2 = tempTrade.factor
                    tempTradeClose.net1 = 0
                    tempTradeClose.net2 = tempTrade.net
                    tempTradeClose.commission1 = tempTrade.commission
                    tempTradeClose.commission2 = tempTrade.commission
                    tempTradeClose.tradeDate1 = tempTrade.matureDate
                    tempTradeClose.tradeDate2 = tempTrade.tradeDate
                    tempTradeClose.settleDate1 = tempTrade.matureDate
                    tempTradeClose.settleDate2 = tempTrade.settleDate
                    tempTradeClose.matureDate = tempTrade.matureDate
                    tempTradeClose.fxRate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
                    tempTradeClose.fxRate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
                    tempTradeClose.principalInUSD1 = 0
                    tempTradeClose.principalInUSD2 = float(tempTradeClose.principal2) * float(tempTradeClose.fxRate2)
                    
                    tempTrade.reserve1 = 0
                    tempTrade.reserve4 = "CLOSED"
                    
                    tempFund = db.fund.Fund()
                    tempSecurity = self.tradeToSecurity(tempTrade)
                    tempFund.fundName = tempTrade.fundName
                    tempFund.securityName = tempTrade.securityName
                    tempFund.securityNo = g.dataBase.qSecurityBySecurityName(tempSecurity)[0].securityNo
                    tempFund.quantity = 0
                    tempFund.position = "C"
                    
                    g.dataBase.uTradeHistoryBySeqNo(tempTrade)
                    g.dataBase.iTradeClose(tempTradeClose)
                    g.dataBase.uFundByCriteria(tempFund)
                    g.dataBase.dTrade(tempTrade)
        for i in putList:
            matureDate = datetime.datetime.strptime(str(i.matureDate),'%Y-%m-%d')
            if datetime.datetime.now() >= matureDate:
                tempTradeList = g.dataBase.qTradeHistoryByISIN(i.ISIN, i.securityType)
                for tempTrade in tempTradeList:
                    tempTradeClose = db.tradeClose.TradeClose()
                    tempTradeClose.seqNo1 = tempTrade.seqNo
                    tempTradeClose.seqNo2 = tempTrade.seqNo
                    tempTradeClose.tranType = tempTrade.tranType
                    tempTradeClose.CUSIP = tempTrade.CUSIP
                    tempTradeClose.ISIN = tempTrade.ISIN
                    tempTradeClose.securityName = tempTrade.securityName
                    tempTradeClose.fundName = tempTrade.fundName
                    tempTradeClose.side2 = tempTrade.side
                    if str(tempTradeClose.side2) ==  "B":
                        tempTradeClose.side1 = "S"
                    else:
                        tempTradeClose.side1 = "B"
                    tempTradeClose.currType1 = tempTrade.currType
                    tempTradeClose.currType2 = tempTrade.currType
                    tempTradeClose.price1 = 0
                    tempTradeClose.price2 = tempTrade.price
                    tempTradeClose.quantity1 = tempTrade.reserve1
                    tempTradeClose.quantity2 = tempTrade.reserve1
                    tempTradeClose.principal1 = 0
                    tempTradeClose.principal2 = tempTrade.principal
                    tempTradeClose.coupon = tempTrade.coupon
                    tempTradeClose.accruedInt1 = tempTrade.accruedInt
                    tempTradeClose.accruedInt2 = tempTrade.accruedInt
                    tempTradeClose.repoRate = tempTrade.repoRate
                    tempTradeClose.factor1 = tempTrade.factor
                    tempTradeClose.factor2 = tempTrade.factor
                    tempTradeClose.net1 = 0
                    tempTradeClose.net2 = tempTrade.net
                    tempTradeClose.commission1 = tempTrade.commission
                    tempTradeClose.commission2 = tempTrade.commission
                    tempTradeClose.tradeDate1 = tempTrade.matureDate
                    tempTradeClose.tradeDate2 = tempTrade.tradeDate
                    tempTradeClose.settleDate1 = tempTrade.matureDate
                    tempTradeClose.settleDate2 = tempTrade.settleDate
                    tempTradeClose.matureDate = tempTrade.matureDate
                    tempTradeClose.fxRate1 = g.dataBase.qCurrencyByDate(tempTradeClose.currType1, tempTradeClose.tradeDate1)[0].rate
                    tempTradeClose.fxRate2 = g.dataBase.qCurrencyByDate(tempTradeClose.currType2, tempTradeClose.tradeDate2)[0].rate
                    tempTradeClose.principalInUSD1 = 0
                    tempTradeClose.principalInUSD2 = float(tempTradeClose.principal2) * float(tempTradeClose.fxRate2)
                    
                    tempTrade.reserve1 = 0
                    tempTrade.reserve4 = "CLOSED"
                    
                    tempFund = db.fund.Fund()
                    tempSecurity = self.tradeToSecurity(tempTrade)
                    tempFund.fundName = tempTrade.fundName
                    tempFund.securityName = tempTrade.securityName
                    tempFund.securityNo = g.dataBase.qSecurityBySecurityName(tempSecurity)[0].securityNo
                    tempFund.quantity = 0
                    tempFund.position = "C"
                    
                    g.dataBase.uTradeHistoryBySeqNo(tempTrade)
                    g.dataBase.iTradeClose(tempTradeClose)
                    g.dataBase.uFundByCriteria(tempFund)
                    g.dataBase.dTrade(tempTrade)
                      
    ''' save account value into database '''
    def updatePnlFromReport(self, accountValue):
        report = db.report.Report()
        wholeReport = g.dataBase.qReport()
        if len(wholeReport) == 0:
            report.tradeDate = g.reportDate
            report.yesAccValue = accountValue
            report.currAccValue = accountValue
            g.dataBase.iReport(report)
        else:
            reportList = g.dataBase.qReportByTradeDate(g.reportDate)
            if len(reportList) == 0 and g.reportDate > wholeReport[0].tradeDate:
                report.tradeDate = g.reportDate
                report.yesAccValue = wholeReport[0].currAccValue
                report.currAccValue = accountValue
                g.dataBase.iReport(report)
            elif len(reportList) > 0:
                report.tradeDate = g.reportDate
                report.yesAccValue = reportList[0].yesAccValue
                report.currAccValue = accountValue
#HELLO ???? WHY AFTER 'UREPORT' STILL NEED COMMITMENT, TO THE SERVER???                 
                g.dataBase.uReport(report)
        g.dataBase.commitment()
    
    ''' calculate daily income attribution '''
    def incomeAttribution(self, fundName, startDate, endDate):
        
        tradeHistoryDict = {}
        incomeAttrDict = {}
        incomeAttrDictRepo = {}
        detailsList = list()
        returnList = list()
        tradeHistoryNew = g.dataBase.qTradeHistoryByDateRange(fundName, endDate, endDate)
        tradeHistoryLast = g.dataBase.qTradeHistoryBeforeDate(startDate)
        tradeHistoryRepoNotClosed = g.dataBase.qTradeHistoryForRepoNotClosed()
        tradeHistoryCRepoNotSettled = g.dataBase.qTradeHistoryForCRepoNotSettled(startDate)
        
        for i in tradeHistoryLast:
            if i.tranType != 'REPO' and i.tranType != 'CREPO':
                if i.ISIN not in tradeHistoryDict:
                    tradeHistoryDict[i.ISIN] = i
                else: 
                    tempQuantity = tradeHistoryDict[i.ISIN].quantity + i.quantity
                    tradeHistoryDict[i.ISIN] = i
                    tradeHistoryDict[i.ISIN].quantity = tempQuantity
        
        for i in tradeHistoryRepoNotClosed:
            s = db.security.Security()
            s.ISIN = i.ISIN
            s.securityType = 'REPO'
            s = g.dataBase.qSecurityBySecurityName(s)[0]
            currFxHistory = g.dataBase.qCurrencyByDate(i.currType, endDate)[0]
            lastFxHistory = g.dataBase.qCurrencyByDate(i.currType, startDate)[0]
            incomeAttr = db.incomeAttribution.IncomeAttribution()
            incomeAttr.securityName = str(s.issuer)
            incomeAttr.securityType = 'REPO'
            incomeAttr.ISIN = i.ISIN
            incomeAttr.coupon = i.coupon
            incomeAttr.matureDate = ''
            incomeAttr.deltaPrice = 0
            incomeAttr.deltaFX = i.price * i.quantity * float(currFxHistory.rate - lastFxHistory.rate) / 100
            incomeAttr.accruedInterest = i.price * i.quantity * i.repoRate * (endDate - startDate).days / 3600000
            incomeAttr.priceFxInteract = 0
            incomeAttr.total = incomeAttr.deltaFX + incomeAttr.accruedInterest
            incomeAttrDictRepo[i.seqNo] = incomeAttr
        
        for i in tradeHistoryCRepoNotSettled:
            s = db.security.Security()
            s.ISIN = i.ISIN
            s.securityType = 'REPO'
            s = g.dataBase.qSecurityBySecurityName(s)[0]
            currFxHistory = g.dataBase.qCurrencyByDate(i.currType, endDate)[0]
            lastFxHistory = g.dataBase.qCurrencyByDate(i.currType, startDate)[0]
            incomeAttr = db.incomeAttribution.IncomeAttribution()
            incomeAttr.securityName = str(s.issuer)
            incomeAttr.securityType = 'CREPO'
            incomeAttr.ISIN = i.ISIN
            incomeAttr.coupon = i.coupon
            incomeAttr.matureDate = ''
            incomeAttr.deltaPrice = 0
            incomeAttr.deltaFX = i.price * i.quantity * float(currFxHistory.rate - lastFxHistory.rate) / 100
            incomeAttr.accruedInterest = i.price * i.quantity * i.repoRate * (endDate - startDate).days / 3600000
            incomeAttr.priceFxInteract = 0
            incomeAttr.total = incomeAttr.deltaFX + incomeAttr.accruedInterest
            #incomeAttrDictRepo[i.seqNo] = incomeAttr
        
        for ISIN, tradeHistory in tradeHistoryDict.items():
            if tradeHistory.quantity == 0:
                pass
            else:
                s = db.security.Security()
                s.ISIN = tradeHistory.ISIN
                s.securityType = tradeHistory.tranType
                s = g.dataBase.qSecurityBySecurityName(s)[0]
                currPriceHistory = g.dataBase.qPriceHistoryAtPriceDate(ISIN, endDate)[0]
                lastPriceHistory = g.dataBase.qPriceHistoryAtPriceDate(ISIN, startDate)[0]
                currFxHistory = g.dataBase.qCurrencyByDate(tradeHistory.currType, endDate)[0]
                lastFxHistory = g.dataBase.qCurrencyByDate(tradeHistory.currType, startDate)[0]
                if tradeHistory.tranType == 'EURO' or tradeHistory.tranType == 'CDS':
                    currPriceHistory.price = currPriceHistory.price / 100
                    lastPriceHistory.price = lastPriceHistory.price / 100
                incomeAttr = db.incomeAttribution.IncomeAttribution()
                incomeAttr.securityName = str(s.issuer)
                incomeAttr.securityType = tradeHistory.tranType
                incomeAttr.ISIN = ISIN
                incomeAttr.coupon = tradeHistory.coupon
                incomeAttr.matureDate = tradeHistory.matureDate
                incomeAttr.quantity = tradeHistory.quantity
                incomeAttr.deltaPrice = (currPriceHistory.price - lastPriceHistory.price) * tradeHistory.quantity \
                    * float(lastFxHistory.rate) * currPriceHistory.factor
                incomeAttr.deltaFX = float(currFxHistory.rate-lastFxHistory.rate) * currPriceHistory.price * tradeHistory.quantity \
                    * currPriceHistory.factor
                if s.reserve4 != 'Y':
                    incomeAttr.accruedInterest = tradeHistory.quantity * tradeHistory.coupon * currPriceHistory.factor \
                        * float(currFxHistory.rate) * (endDate - startDate).days / 36000
                else:
                    incomeAttr.accruedInterest = 0
                    incomeAttr.securityType = 'BOND (defaulted)'
                unrealizedGL = tradeHistory.quantity * currPriceHistory.factor \
                    * (currPriceHistory.price * float(currFxHistory.rate) - lastPriceHistory.price * float(lastFxHistory.rate))
                incomeAttr.total = unrealizedGL + incomeAttr.accruedInterest
                incomeAttr.priceFxInteract = incomeAttr.total - incomeAttr.deltaPrice - incomeAttr.deltaFX - incomeAttr.accruedInterest
                incomeAttrDict[tradeHistory.ISIN] = incomeAttr
        
        for i in tradeHistoryNew:
            if i.tranType != 'REPO' and i.tranType != 'CREPO':
                s = db.security.Security()
                s.ISIN = i.ISIN
                s.securityType = i.tranType
                s = g.dataBase.qSecurityBySecurityName(s)[0]
                incomeAttr = db.incomeAttribution.IncomeAttribution()
                incomeAttr.securityName = str(s.issuer)
                incomeAttr.securityType = i.tranType
                incomeAttr.ISIN = i.ISIN
                incomeAttr.coupon = i.coupon
                incomeAttr.matureDate = i.matureDate
                realizedGL = 0
                unrealizedGL = 0
                if i.ISIN not in incomeAttrDict:
                    currPriceHistory = g.dataBase.qPriceHistoryAtPriceDate(i.ISIN, endDate)[0]
                    currFxHistory = g.dataBase.qCurrencyByDate(i.currType, endDate)[0]
                    if i.tranType == 'EURO' or i.tranType == 'CDS':
                        currPriceHistory.price = currPriceHistory.price / 100
                        i.price = i.price / 100
                    if i.tranType == 'FUT':
                        i.price = i.price / 100
                    incomeAttr.quantity = i.quantity
                    incomeAttr.deltaPrice = (currPriceHistory.price - i.price) * i.quantity * float(currFxHistory.rate) \
                                            * currPriceHistory.factor
                    incomeAttr.deltaFX = 0
                    realizedGL = 0
                    unrealizedGL = i.quantity * currPriceHistory.factor * (currPriceHistory.price - i.price) * float(currFxHistory.rate)
                    incomeAttr.accruedInterest = 0
                    incomeAttr.total = realizedGL + unrealizedGL + incomeAttr.accruedInterest
                    incomeAttr.priceFxInteract = incomeAttr.total - incomeAttr.deltaPrice - incomeAttr.deltaFX \
                                            - incomeAttr.accruedInterest           
                    incomeAttrDict[i.ISIN] = incomeAttr           
                    
                else:
                    currPriceHistory = g.dataBase.qPriceHistoryAtPriceDate(i.ISIN, endDate)[0]
                    try:
                        lastPriceHistory = g.dataBase.qPriceHistoryAtPriceDate(i.ISIN, startDate)[0]
                    except:
                        print(i.ISIN)
                    currFxHistory = g.dataBase.qCurrencyByDate(i.currType, endDate)[0]
                    lastFxHistory = g.dataBase.qCurrencyByDate(i.currType, startDate)[0]
                    if i.tranType == 'EURO' or i.tranType == 'CDS':
                        currPriceHistory.price = currPriceHistory.price / 100
                        lastPriceHistory.price = lastPriceHistory.price / 100
                        i.price = i.price / 100
                    if i.tranType == 'FUT':
                        i.price = i.price / 100
                    if incomeAttrDict[i.ISIN].quantity * i.quantity < 0 and abs(incomeAttrDict[i.ISIN].quantity) >= abs(i.quantity):
                        realizedGL = - i.quantity * currPriceHistory.factor \
                                * (i.price * float(currFxHistory.rate) - lastPriceHistory.price * float(lastFxHistory.rate))
                        unrealizedGL = (incomeAttrDict[i.ISIN].quantity + i.quantity) * currPriceHistory.factor \
                            * (currPriceHistory.price * float(currFxHistory.rate) - lastPriceHistory.price * float(lastFxHistory.rate))
                        incomeAttr.deltaPrice = (incomeAttrDict[i.ISIN].quantity + i.quantity) \
                            * (currPriceHistory.price - lastPriceHistory.price) * float(lastFxHistory.rate) \
                            * currPriceHistory.factor - i.quantity * (i.price - lastPriceHistory.price) \
                            * float(lastFxHistory.rate) * currPriceHistory.factor
                        
                    elif incomeAttrDict[i.ISIN].quantity * i.quantity < 0 and abs(incomeAttrDict[i.ISIN].quantity) < abs(i.quantity):
                        realizedGL = incomeAttrDict[i.ISIN].quantity * currPriceHistory.factor \
                            * (i.price * float(currFxHistory.rate) - lastPriceHistory.price * float(lastFxHistory.rate))
                        unrealizedGL = (incomeAttrDict[i.ISIN].quantity+i.quantity) * currPriceHistory.factor \
                            * (currPriceHistory.price * float(currFxHistory.rate) - i.price * float(currFxHistory.rate))
                        incomeAttr.deltaPrice = (incomeAttrDict[i.ISIN].quantity + i.quantity) \
                            * (currPriceHistory.price-i.price) * float(currFxHistory.rate) * currPriceHistory.factor \
                            + incomeAttrDict[i.ISIN].quantity * (i.price - lastPriceHistory.price) \
                            * float(lastFxHistory.rate) * currPriceHistory.factor 
                    
                    else:
                        realizedGL = 0
                        unrealizedGL = incomeAttrDict[i.ISIN].quantity * currPriceHistory.factor \
                            * (currPriceHistory.price * float(currFxHistory.rate) - lastPriceHistory.price * float(lastFxHistory.rate)) \
                            + i.quantity * (currPriceHistory.price - i.price) * float(currFxHistory.rate)
                        incomeAttr.deltaPrice = i.quantity * (currPriceHistory.price - i.price) * float(currFxHistory.rate) \
                            * currPriceHistory.factor + incomeAttrDict[i.ISIN].quantity \
                            * (currPriceHistory.price - lastPriceHistory.price) * float(lastFxHistory.rate) * currPriceHistory.factor
                    
                    incomeAttr.deltaFX = incomeAttrDict[i.ISIN].quantity * float(currFxHistory.rate - lastFxHistory.rate) \
                            * currPriceHistory.price * currPriceHistory.factor
                    if s.reserve4 != 'Y':
                        incomeAttr.accruedInterest = incomeAttrDict[i.ISIN].quantity * currPriceHistory.factor * i.coupon \
                                                    * float(currFxHistory.rate) * (endDate - startDate).days / 36000
                    else:
                        incomeAttr.accruedInterest = 0
                        incomeAttr.securityType = 'BOND (defaulted)'
                    incomeAttr.total = realizedGL + unrealizedGL + incomeAttr.accruedInterest
                    incomeAttr.quantity = incomeAttrDict[i.ISIN].quantity + i.quantity
                
                    incomeAttr.priceFxInteract = incomeAttr.total - incomeAttr.deltaPrice - incomeAttr.deltaFX \
                                            - incomeAttr.accruedInterest                      
                    incomeAttrDict[i.ISIN].deltaPrice += incomeAttr.deltaPrice
                    incomeAttrDict[i.ISIN].deltaFX += incomeAttr.deltaFX
                    incomeAttrDict[i.ISIN].priceFxInteract += incomeAttr.priceFxInteract
                    incomeAttrDict[i.ISIN].accruedInterest += incomeAttr.accruedInterest
                    incomeAttrDict[i.ISIN].total += incomeAttr.total
                    incomeAttrDict[i.ISIN] = incomeAttr
        
        for ISIN, incomeAttr in incomeAttrDict.items():
            s = db.security.Security()
            s.ISIN = ISIN
            s.securityType = str(incomeAttr.securityType) if incomeAttr.securityType != 'BOND (defaulted)' else 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            detailsDict = {}
            detailsDict['SecurityName'] = incomeAttr.securityName
            detailsDict['Type'] = incomeAttr.securityType if incomeAttr.securityType != 'EURO' else 'BOND'
            detailsDict['Class'] = detailsDict['Type']
            detailsDict['ISIN'] = ISIN
            detailsDict['Country'] = str(securityInfo.category2)
            detailsDict['Coupon'] = incomeAttr.coupon
            detailsDict['Maturity'] = incomeAttr.matureDate if incomeAttr.securityType != 'EQTY' else ''
            detailsDict['Currency'] = str(securityInfo.currType)
            detailsDict['PriceChange'] = incomeAttr.deltaPrice
            detailsDict['InterestEarned'] = incomeAttr.accruedInterest
            detailsDict['FXChange'] = incomeAttr.deltaFX
            detailsDict['PriceFXInteraction'] = incomeAttr.priceFxInteract
            detailsDict['Total'] = incomeAttr.total
            detailsDict['PercentageAttr'] = 0
            detailsDict['PercentageGL'] = 0
            detailsList.append(detailsDict)
        
        for seqNo, incomeAttr in incomeAttrDictRepo.items():
            s = db.security.Security()
            s.ISIN = incomeAttr.ISIN
            s.securityType = 'REPO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            detailsDict = {}
            detailsDict['SecurityName'] = incomeAttr.securityName
            detailsDict['Type'] = 'REPO'
            detailsDict['Class'] = detailsDict['Type']
            detailsDict['ISIN'] = incomeAttr.ISIN
            detailsDict['Country'] = ''
            detailsDict['Coupon'] = incomeAttr.coupon
            detailsDict['Maturity'] = incomeAttr.matureDate
            detailsDict['Currency'] = str(securityInfo.currType)
            detailsDict['PriceChange'] = incomeAttr.deltaPrice
            detailsDict['InterestEarned'] = incomeAttr.accruedInterest
            detailsDict['FXChange'] = incomeAttr.deltaFX
            detailsDict['PriceFXInteraction'] = incomeAttr.priceFxInteract
            detailsDict['Total'] = incomeAttr.total
            detailsDict['PercentageAttr'] = 0
            detailsDict['PercentageGL'] = 0
            detailsList.append(detailsDict)
        
        returnList.append({'Type':'ALL', 'details':detailsList})
        
        return returnList
    
    ''' web scrape SP500 real-time price '''
    def getSP500Price(self):
        #soup = BeautifulSoup(requests.get('https://finance.yahoo.com/quote/%5ESP500TR/history?p=%5ESP500TR').text, "lxml")
        #trs = soup.find_all('tr')
        #price = trs[1].find_all('span')[5].text.replace(',','')
        price=5776.28
        return float(price)  
    
    ''' main entrance to calculate YTD income attribution '''
    def incomeAttributionYTD(self):
        
        incomeAttrDict = {}
        incomeAttrDictRepo = {}
        detailsList = list()
        returnList = list()
        
        year = date.today().year
        startDate = str(year) + '-01-01'
        
        tradeCloseEqtyList = g.dataBase.qTradeCloseForIncomeAttr('EQTY', startDate)
        tradeCloseFutList = g.dataBase.qTradeCloseForIncomeAttr('FUT', startDate)
        tradeCloseCallList = g.dataBase.qTradeCloseForIncomeAttr('CALL', startDate)
        tradeClosePutList = g.dataBase.qTradeCloseForIncomeAttr('PUT', startDate)
        tradeCloseCDSList = g.dataBase.qTradeCloseForIncomeAttr('CDS', startDate)
        tradeCloseBondList = g.dataBase.qTradeCloseForIncomeAttr('EURO', startDate)
        tradeCloseRepoList = g.dataBase.qTradeCloseForIncomeAttr('CREPO', startDate)
        
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeCloseEqtyList, 'EQTY')
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeCloseFutList, 'FUT')
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeCloseCallList, 'CALL')
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeClosePutList, 'PUT')
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeCloseCDSList, 'CDS')
        self.tradeCloseForIncomeAttribution(incomeAttrDict, tradeCloseBondList, 'BOND')
        self.tradeCloseForIncomeAttribution(incomeAttrDictRepo, tradeCloseRepoList, 'REPO')
                    
        tradeHistoryEqtyNotClosedList = g.dataBase.qTradeHistoryByCriteria5('EQTY')
        tradeHistoryFutNotClosedList = g.dataBase.qTradeHistoryByCriteria5('FUT')
        tradeHistoryCallNotClosedList = g.dataBase.qTradeHistoryByCriteria5('CALL')
        tradeHistoryPutNotClosedList = g.dataBase.qTradeHistoryByCriteria5('PUT')
        tradeHistoryCdsNotClosedList = g.dataBase.qTradeHistoryByCriteria5('CDS')
        tradeHistoryBondNotClosedList = g.dataBase.qTradeHistoryByCriteria5('EURO')
        tradeHistoryRepoNotClosedList = g.dataBase.qTradeHistoryByCriteria5('REPO')
         
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryEqtyNotClosedList, 'EQTY')
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryFutNotClosedList, 'FUT')
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryCallNotClosedList, 'CALL')
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryPutNotClosedList, 'PUT')
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryCdsNotClosedList, 'CDS')
        self.tradeHistoryForIncomeAttribution(incomeAttrDict, tradeHistoryBondNotClosedList, 'BOND')
        self.tradeHistoryForIncomeAttribution(incomeAttrDictRepo, tradeHistoryRepoNotClosedList, 'REPO')
        
        self.detailListForIncomeAttribution(incomeAttrDict, detailsList)
        self.detailListForIncomeAttribution(incomeAttrDictRepo, detailsList)
        
        returnList.append({'Type':'ALL', 'details':detailsList})
        
        return returnList
    
    ''' main entrance to calculate MTD income attribution '''
    def incomeAttributionMTD(self):
        
        incomeAttrDict = {}
        incomeAttrDictRepo = {}
        detailsList = list()
        returnList = list()
        
        year = date.today().year
        month = date.today().month
        startDate = str(year) + '-' + str(month) + '-01'
        
        tradeCloseEqtyList = g.dataBase.qTradeCloseForIncomeAttr('EQTY', startDate)
        tradeCloseFutList = g.dataBase.qTradeCloseForIncomeAttr('FUT', startDate)
        tradeCloseCallList = g.dataBase.qTradeCloseForIncomeAttr('CALL', startDate)
        tradeClosePutList = g.dataBase.qTradeCloseForIncomeAttr('PUT', startDate)
        tradeCloseCDSList = g.dataBase.qTradeCloseForIncomeAttr('CDS', startDate)
        tradeCloseBondList = g.dataBase.qTradeCloseForIncomeAttr('EURO', startDate)
        tradeCloseRepoList = g.dataBase.qTradeCloseForIncomeAttr('CREPO', startDate)
        
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeCloseEqtyList, 'EQTY')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeCloseFutList, 'FUT')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeCloseCallList, 'CALL')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeClosePutList, 'PUT')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeCloseCDSList, 'CDS')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDict, tradeCloseBondList, 'BOND')
        self.tradeCloseForIncomeAttributionMTD(incomeAttrDictRepo, tradeCloseRepoList, 'REPO')
                    
        tradeHistoryEqtyNotClosedList = g.dataBase.qTradeHistoryByCriteria5('EQTY')
        tradeHistoryFutNotClosedList = g.dataBase.qTradeHistoryByCriteria5('FUT')
        tradeHistoryCallNotClosedList = g.dataBase.qTradeHistoryByCriteria5('CALL')
        tradeHistoryPutNotClosedList = g.dataBase.qTradeHistoryByCriteria5('PUT')
        tradeHistoryCdsNotClosedList = g.dataBase.qTradeHistoryByCriteria5('CDS')
        tradeHistoryBondNotClosedList = g.dataBase.qTradeHistoryByCriteria5('EURO')
        tradeHistoryRepoNotClosedList = g.dataBase.qTradeHistoryByCriteria5('REPO')
         
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryEqtyNotClosedList, 'EQTY')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryFutNotClosedList, 'FUT')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryCallNotClosedList, 'CALL')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryPutNotClosedList, 'PUT')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryCdsNotClosedList, 'CDS')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDict, tradeHistoryBondNotClosedList, 'BOND')
        self.tradeHistoryForIncomeAttributionMTD(incomeAttrDictRepo, tradeHistoryRepoNotClosedList, 'REPO')
        
        self.detailListForIncomeAttribution(incomeAttrDict, detailsList)
        self.detailListForIncomeAttribution(incomeAttrDictRepo, detailsList)
        
        returnList.append({'Type':'ALL', 'details':detailsList})
        
        return returnList
    
    ''' calculate YTD income attribution for closed trades '''
    def tradeCloseForIncomeAttribution(self, incomeAttrDict, tradeCloseList, securityType):
        year = date.today().year
        previousDate = (datetime.date(year, 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        for tradeClose in tradeCloseList:
            if tradeClose.currType1 != 'USD':
                if tradeClose.tradeDate2 < datetime.date(year, 1, 1):
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, previousDate)[0].rate)
                else:
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, tradeClose.tradeDate2)[0].rate)
                fx2 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, tradeClose.tradeDate1)[0].rate)
            else:
                fx1, fx2 = 1, 1
            
            if securityType != 'BOND':
                factor1, factor2 = 1, 1
            else:
                if tradeClose.tradeDate2 < datetime.date(year, 1, 1):
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, previousDate)[0].factor)
                else:
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, tradeClose.tradeDate2)[0].factor)
                factor2 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, tradeClose.tradeDate1)[0].factor)
            
            if tradeClose.tradeDate2 < datetime.date(year, 1, 1):
                if securityType == 'REPO':
                    price1 = float(tradeClose.price2) / 100
                else:
                    price1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, previousDate)[0].price)
                    if securityType == 'CDS' or securityType == 'BOND':
                        price1 = price1 / 100
            else:
                if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                    price1 = float(tradeClose.price2) / 100
                else:
                    price1 = float(tradeClose.price2)
            
            if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                price2 = float(tradeClose.price1) / 100
            else:
                price2 = float(tradeClose.price1)
            
            price1 *= factor1
            price2 *= factor2
            
            if tradeClose.ISIN not in incomeAttrDict:
                ia = db.incomeAttribution.IncomeAttribution()
                ia.securityType = securityType
                if tradeClose.side1 == 'S':
                    ia.total = (price2 * fx2 - price1 * fx1) * float(tradeClose.quantity1)
                    ia.deltaPrice = (price2 * fx1 - price1 * fx1) * float(tradeClose.quantity1)
                    ia.deltaFX = (price2 * fx2 - price2 * fx1) * float(tradeClose.quantity1)
                    if ia.securityType == 'CDS' or securityType == 'BOND':
                        ia.accruedInterest = self.intEarnedForBondCdsClosed(tradeClose)
                        ia.total += self.intEarnedForBondCdsClosed(tradeClose)
                    elif securityType == 'REPO':
                        daysThisYear = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, 1, 1) - timedelta(days=1))).days
                        daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                        ia.accruedInterest = float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
                        ia.total += float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
                    incomeAttrDict[tradeClose.ISIN] = ia
                else:
                    ia.total = (price1 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    ia.deltaPrice = (price1 * fx1 - price2 * fx1) * float(tradeClose.quantity1)
                    ia.deltaFX = (price2 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    if ia.securityType == 'CDS' or securityType == 'BOND':
                        ia.accruedInterest = self.intEarnedForBondCdsClosed(tradeClose)
                        ia.total += self.intEarnedForBondCdsClosed(tradeClose)
                    elif securityType == 'REPO':
                        daysThisYear = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, 1, 1) - timedelta(days=1))).days
                        daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                        ia.accruedInterest = float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
                        ia.total += float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
                    incomeAttrDict[tradeClose.ISIN] = ia
            else:
                if tradeClose.side1 == 'S':
                    incomeAttrDict[tradeClose.ISIN].total += (price2 * fx2 - price1 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaPrice += (price2 * fx1 - price1 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaFX += (price2 * fx2 - price2 * fx1) * float(tradeClose.quantity1)
                else:
                    incomeAttrDict[tradeClose.ISIN].total += (price1 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaPrice += (price1 * fx1 - price2 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaFX += (price2 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                if securityType == 'CDS' or securityType == 'BOND':
                    incomeAttrDict[tradeClose.ISIN].accruedInterest += self.intEarnedForBondCdsClosed(tradeClose)
                    incomeAttrDict[tradeClose.ISIN].total += self.intEarnedForBondCdsClosed(tradeClose)
                if securityType == 'REPO':
                    daysThisYear = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, 1, 1) - timedelta(days=1))).days
                    daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                    incomeAttrDict[tradeClose.ISIN].accruedInterest += float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
                    incomeAttrDict[tradeClose.ISIN].total += float(tradeClose.accruedInt1) * fx2 * daysThisYear / daysAll
    
    ''' calculate MTD income attribution for close trades '''
    def tradeCloseForIncomeAttributionMTD(self, incomeAttrDict, tradeCloseList, securityType):
        year = date.today().year
        month = date.today().month
        temppreviousDate = (datetime.date(year, month, 1) - timedelta(days=1))
        while temppreviousDate.weekday()>4:
            temppreviousDate=temppreviousDate - timedelta(days=1)
        previousDate=temppreviousDate.strftime("%Y-%m-%d")
        
        for tradeClose in tradeCloseList:
            if tradeClose.currType1 != 'USD':
                if tradeClose.tradeDate2 < datetime.date(year, month, 1):
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, previousDate)[0].rate)
                else:
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, tradeClose.tradeDate2)[0].rate)
                fx2 = float(g.dataBase.qCurrencyByDate(tradeClose.currType1, tradeClose.tradeDate1)[0].rate)
            else:
                fx1, fx2 = 1, 1
            
            if securityType != 'BOND':
                factor1, factor2 = 1, 1
            else:
                if tradeClose.tradeDate2 < datetime.date(year, month, 1):
                    try:
                        factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, previousDate)[0].factor)
                    except:
                        print(previousDate)
                        print(tradeClose.ISIN)
                else:
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, tradeClose.tradeDate2)[0].factor)
                factor2 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, tradeClose.tradeDate1)[0].factor)
            
            if tradeClose.tradeDate2 < datetime.date(year, month, 1):
                if securityType == 'REPO':
                    price1 = float(tradeClose.price2) / 100
                else:
                    price1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeClose.ISIN, previousDate)[0].price)
                    if securityType == 'CDS' or securityType == 'BOND':
                        price1 = price1 / 100
            else:
                if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                    price1 = float(tradeClose.price2) / 100
                else:
                    price1 = float(tradeClose.price2)
            
            if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                price2 = float(tradeClose.price1) / 100
            else:
                price2 = float(tradeClose.price1)
            
            price1 *= factor1
            price2 *= factor2
            
            if tradeClose.ISIN not in incomeAttrDict:
                ia = db.incomeAttribution.IncomeAttribution()
                ia.securityType = securityType
                if tradeClose.side1 == 'S':
                    ia.total = (price2 * fx2 - price1 * fx1) * float(tradeClose.quantity1)
                    ia.deltaPrice = (price2 * fx1 - price1 * fx1) * float(tradeClose.quantity1)
                    ia.deltaFX = (price2 * fx2 - price2 * fx1) * float(tradeClose.quantity1)
                    if ia.securityType == 'CDS' or securityType == 'BOND':
                        ia.accruedInterest = self.intEarnedForBondCdsClosedMTD(tradeClose)
                        ia.total += self.intEarnedForBondCdsClosedMTD(tradeClose)
                    elif securityType == 'REPO':
                        daysThisMonth = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, month, 1) - timedelta(days=1))).days
                        daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                        ia.accruedInterest = float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
                        ia.total += float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
                    incomeAttrDict[tradeClose.ISIN] = ia
                else:
                    ia.total = (price1 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    ia.deltaPrice = (price1 * fx1 - price2 * fx1) * float(tradeClose.quantity1)
                    ia.deltaFX = (price2 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    if ia.securityType == 'CDS' or securityType == 'BOND':
                        ia.accruedInterest = self.intEarnedForBondCdsClosedMTD(tradeClose)
                        ia.total += self.intEarnedForBondCdsClosedMTD(tradeClose)
                    elif securityType == 'REPO':
                        daysThisMonth = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, month, 1) - timedelta(days=1))).days
                        daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                        ia.accruedInterest = float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
                        ia.total += float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
                    incomeAttrDict[tradeClose.ISIN] = ia
            else:
                if tradeClose.side1 == 'S':
                    incomeAttrDict[tradeClose.ISIN].total += (price2 * fx2 - price1 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaPrice += (price2 * fx1 - price1 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaFX += (price2 * fx2 - price2 * fx1) * float(tradeClose.quantity1)
                else:
                    incomeAttrDict[tradeClose.ISIN].total += (price1 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaPrice += (price1 * fx1 - price2 * fx1) * float(tradeClose.quantity1)
                    incomeAttrDict[tradeClose.ISIN].deltaFX += (price2 * fx1 - price2 * fx2) * float(tradeClose.quantity1)
                if securityType == 'CDS' or securityType == 'BOND':
                    incomeAttrDict[tradeClose.ISIN].accruedInterest += self.intEarnedForBondCdsClosedMTD(tradeClose)
                    incomeAttrDict[tradeClose.ISIN].total += self.intEarnedForBondCdsClosedMTD(tradeClose)
                if securityType == 'REPO':
                    daysThisMonth = (tradeClose.tradeDate1 - max(tradeClose.tradeDate2, datetime.date(year, month, 1) - timedelta(days=1))).days
                    daysAll = (tradeClose.tradeDate1 - tradeClose.tradeDate2).days
                    incomeAttrDict[tradeClose.ISIN].accruedInterest += float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
                    incomeAttrDict[tradeClose.ISIN].total += float(tradeClose.accruedInt1) * fx2 * daysThisMonth / daysAll
    
    ''' calculate YTD income attribution for open trades '''
    def tradeHistoryForIncomeAttribution(self, incomeAttrDict, tradeHistoryNotClosedList, securityType):
        year = date.today().year
        temppreviousDate = datetime.date(year, 1, 1) - timedelta(days=1)
        while temppreviousDate.weekday()>4:
            temppreviousDate=temppreviousDate - timedelta(days=1)
        previousDate=temppreviousDate.strftime("%Y-%m-%d")
        
        for tradeHistory in tradeHistoryNotClosedList:
            
            if str(tradeHistory.currType) != 'USD':
                if tradeHistory.tradeDate < datetime.date(year, 1, 1):
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeHistory.currType, previousDate)[0].rate)
                else:
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeHistory.currType, tradeHistory.tradeDate)[0].rate)
                fx2 = float(g.dataBase.qLatestCurrency(tradeHistory.currType)[0].rate)
            else:
                fx1, fx2 = 1, 1
            
            if securityType != 'BOND':
                factor1, factor2 = 1, 1
            else:
                if tradeHistory.tradeDate < datetime.date(year, 1, 1):
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, previousDate)[0].factor)
                else:
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, tradeHistory.tradeDate)[0].factor)
                factor2 = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].factor)
            
            if tradeHistory.tradeDate < datetime.date(year, 1, 1):
                if securityType == 'REPO':
                    price1 = float(tradeHistory.price) / 100
                else:
                    price1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, previousDate)[0].price)
                    if securityType == 'CDS' or securityType == 'BOND':
                        price1 = price1 / 100
            else:
                if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                    price1 = float(tradeHistory.price) / 100
                else:
                    price1 = float(tradeHistory.price)
            
            if securityType == 'REPO':
                price2 = price1
            else:
                price2 = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].price)
                if securityType == 'CDS' or securityType == 'BOND':
                    price2 = price2 / 100
            
            price1 *= factor1
            price2 *= factor2
            
            if str(tradeHistory.ISIN) not in incomeAttrDict:
                ia = db.incomeAttribution.IncomeAttribution()
                ia.securityType = securityType
                if tradeHistory.side == 'B':
                    ia.total = (price2 * fx2 - price1 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaPrice = (price2 * fx1 - price1 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaFX = (price2 * fx2 - price2 * fx1) * float(tradeHistory.reserve1)
                else:
                    ia.total = (price1 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                    ia.deltaPrice = (price1 * fx1 - price2 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaFX = (price2 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                if securityType == 'REPO':
                    ia.accruedInterest = self.intEarnedForRepoNotClosed(tradeHistory, price2, fx2)
                    ia.total += ia.accruedInterest
                if ia.securityType == 'CDS' or securityType == 'BOND':
                    ia.accruedInterest = self.intEarnedForBondCdsNotClosed(tradeHistory, fx2)
                    ia.total += ia.accruedInterest
                incomeAttrDict[str(tradeHistory.ISIN)] = ia
            else:
                if tradeHistory.side == 'B':
                    incomeAttrDict[str(tradeHistory.ISIN)].total += (price2 * fx2 - price1 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaPrice += (price2 * fx1 - price1 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaFX += (price2 * fx2 - price2 * fx1) * float(tradeHistory.reserve1)
                else:
                    incomeAttrDict[str(tradeHistory.ISIN)].total += (price1 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaPrice += (price1 * fx1 - price2 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaFX += (price2 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                if securityType == 'REPO':
                    incomeAttrDict[str(tradeHistory.ISIN)].accruedInterest += self.intEarnedForRepoNotClosed(tradeHistory, price2, fx2)
                    incomeAttrDict[str(tradeHistory.ISIN)].total += incomeAttrDict[str(tradeHistory.ISIN)].accruedInterest
                if securityType == 'CDS' or securityType == 'BOND':
                    incomeAttrDict[str(tradeHistory.ISIN)].accruedInterest += self.intEarnedForBondCdsNotClosed(tradeHistory, fx2)
                    incomeAttrDict[str(tradeHistory.ISIN)].total += self.intEarnedForBondCdsNotClosed(tradeHistory, fx2)
    
    ''' calculate MTD income attribution for open trades '''
    def tradeHistoryForIncomeAttributionMTD(self, incomeAttrDict, tradeHistoryNotClosedList, securityType):
        year = date.today().year
        month = date.today().month
        temppreviousDate = (datetime.date(year, month, 1) - timedelta(days=1))
        while temppreviousDate.weekday()>4:
            temppreviousDate=temppreviousDate - timedelta(days=1)
        previousDate=temppreviousDate.strftime("%Y-%m-%d")
        
        for tradeHistory in tradeHistoryNotClosedList:
            
            if str(tradeHistory.currType) != 'USD':
                if tradeHistory.tradeDate < datetime.date(year, month, 1):
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeHistory.currType, previousDate)[0].rate)
                else:
                    fx1 = float(g.dataBase.qCurrencyByDate(tradeHistory.currType, tradeHistory.tradeDate)[0].rate)
                fx2 = float(g.dataBase.qLatestCurrency(tradeHistory.currType)[0].rate)
            else:
                fx1, fx2 = 1, 1
            
            if securityType != 'BOND':
                factor1, factor2 = 1, 1
            else:
                if tradeHistory.tradeDate < datetime.date(year, month, 1):
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, previousDate)[0].factor)
                else:
                    factor1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, tradeHistory.tradeDate)[0].factor)
                factor2 = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].factor)
            
            if tradeHistory.tradeDate < datetime.date(year, month, 1):
                if securityType == 'REPO':
                    price1 = float(tradeHistory.price) / 100
                else:
                    price1 = float(g.dataBase.qPriceHistoryAtPriceDate(tradeHistory.ISIN, previousDate)[0].price)
                    if securityType == 'CDS' or securityType == 'BOND':
                        price1 = price1 / 100
            else:
                if securityType == 'FUT' or securityType == 'REPO' or securityType == 'CDS' or securityType == 'BOND':
                    price1 = float(tradeHistory.price) / 100
                else:
                    price1 = float(tradeHistory.price)
            
            if securityType == 'REPO':
                price2 = price1
            else:
                price2 = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].price)
                if securityType == 'CDS' or securityType == 'BOND':
                    price2 = price2 / 100
            
            price1 *= factor1
            price2 *= factor2
            
            if str(tradeHistory.ISIN) not in incomeAttrDict:
                ia = db.incomeAttribution.IncomeAttribution()
                ia.securityType = securityType
                if tradeHistory.side == 'B':
                    ia.total = (price2 * fx2 - price1 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaPrice = (price2 * fx1 - price1 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaFX = (price2 * fx2 - price2 * fx1) * float(tradeHistory.reserve1)
                else:
                    ia.total = (price1 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                    ia.deltaPrice = (price1 * fx1 - price2 * fx1) * float(tradeHistory.reserve1)
                    ia.deltaFX = (price2 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                if securityType == 'REPO':
                    ia.accruedInterest = self.intEarnedForRepoNotClosedMTD(tradeHistory, price2, fx2)
                    ia.total += self.intEarnedForRepoNotClosedMTD(tradeHistory, price2, fx2)
                if ia.securityType == 'CDS' or securityType == 'BOND':
                    ia.accruedInterest = self.intEarnedForBondCdsNotClosedMTD(tradeHistory, fx2)
                    ia.total += self.intEarnedForBondCdsNotClosedMTD(tradeHistory, fx2)
                incomeAttrDict[str(tradeHistory.ISIN)] = ia
            else:
                if tradeHistory.side == 'B':
                    incomeAttrDict[str(tradeHistory.ISIN)].total += (price2 * fx2 - price1 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaPrice += (price2 * fx1 - price1 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaFX += (price2 * fx2 - price2 * fx1) * float(tradeHistory.reserve1)
                else:
                    incomeAttrDict[str(tradeHistory.ISIN)].total += (price1 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaPrice += (price1 * fx1 - price2 * fx1) * float(tradeHistory.reserve1)
                    incomeAttrDict[str(tradeHistory.ISIN)].deltaFX += (price2 * fx1 - price2 * fx2) * float(tradeHistory.reserve1)
                if securityType == 'REPO':
                    incomeAttrDict[str(tradeHistory.ISIN)].accruedInterest += self.intEarnedForRepoNotClosedMTD(tradeHistory, price2, fx2)
                    incomeAttrDict[str(tradeHistory.ISIN)].total += self.intEarnedForRepoNotClosedMTD(tradeHistory, price2, fx2)
                if securityType == 'CDS' or securityType == 'BOND':
                    incomeAttrDict[str(tradeHistory.ISIN)].accruedInterest += self.intEarnedForBondCdsNotClosedMTD(tradeHistory, fx2)
                    incomeAttrDict[str(tradeHistory.ISIN)].total += self.intEarnedForBondCdsNotClosedMTD(tradeHistory, fx2)

    def detailListForIncomeAttribution(self, incomeAttrDict, detailsList):
        for ISIN, ia in incomeAttrDict.items():
            s = db.security.Security()
            s.ISIN = ISIN
            s.securityType = ia.securityType if ia.securityType != 'BOND' else 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            detailsDict = {}
            detailsDict['SecurityName'] = str(securityInfo.securityName)
            detailsDict['Type'] = ia.securityType
            detailsDict['Class'] = ia.securityType
            detailsDict['ISIN'] = ISIN
            if ia.securityType == 'REPO':
                detailsDict['Country'] = ''
            else:
                detailsDict['Country'] = str(securityInfo.category2)
            detailsDict['Coupon'] = round(float(securityInfo.coupon), 2)
            if ia.securityType == 'EQTY' or ia.securityType == 'REPO':
                detailsDict['Maturity'] = ''
            else:
                tempDate = securityInfo.matureDate
                year = str(tempDate.year)
                month = str(tempDate.month)
                day = str(tempDate.day)
                detailsDict['Maturity'] = month + '/' + day + '/' + year
            detailsDict['Currency'] = str(securityInfo.currType)
            detailsDict['PriceChange'] = int(ia.deltaPrice)
            detailsDict['InterestEarned'] = int(ia.accruedInterest)
            detailsDict['FXChange'] = int(ia.deltaFX)
            detailsDict['PriceFXInteraction'] = int(ia.total - ia.deltaPrice - ia.deltaFX)
            detailsDict['Total'] = int(ia.total)
            detailsDict['PercentageAttr'] = 0
            detailsDict['PercentageGL'] = 0
            detailsList.append(detailsDict)
    
    ''' calculate YTD interest earned for open repos '''
    def intEarnedForRepoNotClosed(self, tradeHistory, price, fx):
        year = date.today().year
        previousDate = datetime.date(year, 1, 1) - timedelta(days=1)
        settleDate = max(tradeHistory.settleDate, previousDate)
        today = date.today()
        if (today - settleDate).days > 0:
            interest = float(tradeHistory.reserve1) * price * float(tradeHistory.repoRate) * fx * (today - settleDate).days / 36000
        else:
            interest = 0
        if tradeHistory.side == 'S':
            return -interest
        else:
            return interest
    
    ''' calculate MTD interest earned for open repos '''
    def intEarnedForRepoNotClosedMTD(self, tradeHistory, price, fx):
        year = date.today().year
        month = date.today().month
        settleDate = max(tradeHistory.settleDate, datetime.date(year, month, 1) - timedelta(days=1))
        today = date.today()
        if (today - settleDate).days > 0:
            interest = float(tradeHistory.reserve1) * price * float(tradeHistory.repoRate) * fx * (today - settleDate).days / 36000
        else:
            interest = 0
        if tradeHistory.side == 'S':
            return -interest
        else:
            return interest
    
    ''' calculate YTD interest earned for open bonds & CDS '''
    def intEarnedForBondCdsNotClosed(self, tradeHistory, fx):
        year = date.today().year
        previousDate = datetime.date(year, 1, 1) - timedelta(days=1)
        if tradeHistory.tranType == 'CDS':
            settleDate = max(tradeHistory.settleDate, previousDate)
            today = date.today()
            if (today - settleDate).days > 0:
                interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (today - settleDate).days / 36000
            else:
                interest = 0
        elif tradeHistory.tranType == 'EURO':
            s = db.security.Security()
            s.ISIN = tradeHistory.ISIN
            s.securityType = 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].factor)
            if str(securityInfo.reserve4) != 'Y':
                settleDate = max(tradeHistory.settleDate, previousDate)
                today = date.today()
                if (today - settleDate).days > 0:
                    interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (today - settleDate).days * factor / 36000
                else:
                    interest = 0
            else:
                expectedLastCoupDt = securityInfo.firstCoupDt
                couponFreq = int(securityInfo.couponFreq)
                while expectedLastCoupDt < securityInfo.lastCoupDt:
                    expectedLastCoupDt += relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt > securityInfo.firstCoupDt:
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt < max(tradeHistory.settleDate, previousDate):
                    interest = 0
                else:
                    settleDate1 = max(tradeHistory.settleDate, previousDate)
                    settleDate2 = expectedLastCoupDt
                    interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (settleDate2 - settleDate1).days \
                                * factor / 36000
        if tradeHistory.side == 'S':
            return -interest
        else:
            return interest
    
    ''' calculate MTD interest earned for open bonds & CDS '''
    def intEarnedForBondCdsNotClosedMTD(self, tradeHistory, fx):
        year = date.today().year
        month = date.today().month
        if tradeHistory.tranType == 'CDS':
            settleDate = max(tradeHistory.settleDate, datetime.date(year, month, 1) - timedelta(days=1))
            today = date.today()
            if (today - settleDate).days > 0:
                interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (today - settleDate).days / 36000
            else:
                interest = 0
        elif tradeHistory.tranType == 'EURO':
            s = db.security.Security()
            s.ISIN = tradeHistory.ISIN
            s.securityType = 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeHistory.ISIN, date.today())[0].factor)
            if str(securityInfo.reserve4) != 'Y':
                settleDate = max(tradeHistory.settleDate, datetime.date(year, month, 1) - timedelta(days=1))
                today = date.today()
                if (today - settleDate).days > 0:
                    interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (today - settleDate).days * factor / 36000
                else:
                    interest = 0
            else:
                expectedLastCoupDt = securityInfo.firstCoupDt
                couponFreq = int(securityInfo.couponFreq)
                while expectedLastCoupDt < securityInfo.lastCoupDt:
                    expectedLastCoupDt += relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt > securityInfo.firstCoupDt:
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt < max(tradeHistory.settleDate, datetime.date(year, month, 1) - timedelta(days=1)):
                    interest = 0
                else:
                    settleDate1 = max(tradeHistory.settleDate, datetime.date(year, month, 1) - timedelta(days=1))
                    settleDate2 = expectedLastCoupDt
                    interest = float(tradeHistory.reserve1) * float(tradeHistory.coupon) * fx * (settleDate2 - settleDate1).days \
                                * factor / 36000
        if tradeHistory.side == 'S':
            return -interest
        else:
            return interest
    
    ''' calculate YTD interest earned for closed bonds & CDS '''
    def intEarnedForBondCdsClosed(self, tradeClose):
        year = date.today().year
        previousDate = datetime.date(year, 1, 1) - timedelta(days=1)
        if tradeClose.tranType == 'CDS':
            settleDate1 = max(tradeClose.settleDate2, previousDate)
            settleDate2 = tradeClose.settleDate1
            interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) \
                        * (settleDate2 - settleDate1).days / 360
        elif tradeClose.tranType == 'EURO':
            s = db.security.Security()
            s.ISIN = tradeClose.ISIN
            s.securityType = 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            if str(securityInfo.reserve4) != 'Y':
                settleDate1 = max(tradeClose.settleDate2, previousDate)
                settleDate2 = tradeClose.settleDate1
                factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeClose.ISIN, settleDate2)[0].factor)
                interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) * factor \
                            * (settleDate2 - settleDate1).days / 360
            else:
                expectedLastCoupDt = securityInfo.firstCoupDt
                couponFreq = int(securityInfo.couponFreq)
                while expectedLastCoupDt < securityInfo.lastCoupDt:
                    expectedLastCoupDt += relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt > securityInfo.firstCoupDt:
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt < max(tradeClose.settleDate2, previousDate):
                    interest = 0
                else:
                    settleDate1 = max(tradeClose.settleDate2, previousDate)
                    settleDate2 = expectedLastCoupDt
                    factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeClose.ISIN, settleDate2)[0].factor)
                    interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) * factor \
                            * (settleDate2 - settleDate1).days / 360
                
        if tradeClose.side1 == 'B':
            return -interest
        else:
            return interest
    
    ''' calculate MTD interest earned for closed bonds & CDS '''
    def intEarnedForBondCdsClosedMTD(self, tradeClose):
        year = date.today().year
        month = date.today().month
        previousDate = (datetime.date(year, month, 1) - timedelta(days=1))
        settleDate1 = max(previousDate, tradeClose.settleDate2)
        if tradeClose.tranType == 'CDS':
            settleDate2 = tradeClose.settleDate1
            
            interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) \
                        * (settleDate2 - settleDate1).days / 360
        elif tradeClose.tranType == 'EURO':
            s = db.security.Security()
            s.ISIN = tradeClose.ISIN
            s.securityType = 'EURO'
            securityInfo = g.dataBase.qSecurityBySecurityName(s)[0]
            if str(securityInfo.reserve4) != 'Y':

                settleDate2 = tradeClose.settleDate1
                factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeClose.ISIN, settleDate2)[0].factor)
                interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) * factor \
                            * (settleDate2 - settleDate1).days / 360
            else:
                expectedLastCoupDt = securityInfo.firstCoupDt
                couponFreq = int(securityInfo.couponFreq)
                while expectedLastCoupDt < securityInfo.lastCoupDt:
                    expectedLastCoupDt += relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt > securityInfo.firstCoupDt:
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                    expectedLastCoupDt -= relativedelta(months = 12 / couponFreq)
                if expectedLastCoupDt < tradeClose.settleDate2:
                    interest = 0
                else:
                    settleDate2 = expectedLastCoupDt
                    factor = float(g.dataBase.qPriceHistoryByPriceDate(tradeClose.ISIN, settleDate2)[0].factor)
                    interest = float(tradeClose.quantity1) * (float(tradeClose.coupon)/100) * float(tradeClose.fxRate1) * factor \
                            * (settleDate2 - settleDate1).days / 360
                
        if tradeClose.side1 == 'B':
            return -interest
        else:
            return interest
    
    ''' generate unrealized G/L report '''
#HELLO ??? CONFUSE about this method        
    def unRealizedDetails(self, unrzGlList, openPositions, cashPositions):
        bondDict = {}
        equityDict = {}
        futureDict = {}
        repoDict = {}
        optionDict = {}
        cdsDict = {}
        cashDict = {}
        
        bondDict['categoryName'] = "BOND"
        bondDict['class'] = "bond"
        bondDict['details'] = []
        equityDict['categoryName'] = "EQUITY"
        equityDict['class'] = "equity"
        equityDict['details'] = []
        futureDict['categoryName'] = "FUTURE"
        futureDict['class'] = "future"
        futureDict['details'] = []
        repoDict['categoryName'] = "REPO"
        repoDict['class'] = "repo"
        repoDict['details'] = []
        optionDict['categoryName'] = "OPTION"
        optionDict['class'] = "option"
        optionDict['details'] = []
        cdsDict['categoryName'] = "CDS"
        cdsDict['class'] = "cds"
        cdsDict['details'] = []
        cashDict['categoryName'] = "CASH"
        cashDict['class'] = "cash"
        cashDict['details'] = []
        
        for op in openPositions:
            tempDict = {}
            tempList = op['CbDetails']
            tempUnrzGL = db.realizedGL.RealizedGL()
            tempUnrzGL.securityName = op['Issuer']
            tempUnrzGL.securityType = op['Category']
            tempUnrzGL.country = op['Country']
            for cb in tempList:
                tempYear = int(cb['TradeDate'][-4:])
                if tempYear < date.today().year:
                    tempUnrzGL.ltGain += cb['Pnl']
                else:
                    tempUnrzGL.stGain += cb['Pnl']
            tempUnrzGL.total = tempUnrzGL.ltGain + tempUnrzGL.stGain
            tempDict['costBasis'] = op['CbDetails']
            tempDict['Coupon'] = op['Coupon']
            tempDict['Maturity'] = op['Maturity']
            tempDict['Currency'] = op['Currency']
            tempDict['SecurityName'] = str(g.dataBase.qSecurityByISIN(op['ISIN'])[0].securityName)
            tempDict['Country'] = op['Country']
            tempDict['Cost'] = '-'
            tempDict['Proceeds'] = '-'
            tempDict['stgainloss'] = tempUnrzGL.stGain
            tempDict['ltgainloss'] = tempUnrzGL.ltGain
            tempDict['intexp'] = '-'
            tempDict['intrev'] = '-'
            tempDict['totalrlzusd'] = tempUnrzGL.total
            tempDict['ISIN'] = op['ISIN']
            tempDict['ordinaryIncome'] = 0
            tempDict['totalrlz'] = 0
            if tempUnrzGL.securityType == "BOND" or tempUnrzGL.securityType == "BOND (defaulted)":
                bondDict['details'].append(tempDict)
            if tempUnrzGL.securityType == "EQTY":
                equityDict['details'].append(tempDict)
            if tempUnrzGL.securityType == "FUT":
                futureDict['details'].append(tempDict)
            if tempUnrzGL.securityType == "CALL" or tempUnrzGL.securityType == "PUT":
                optionDict['details'].append(tempDict)
            if tempUnrzGL.securityType == "CDS":
                cdsDict['details'].append(tempDict)
            if tempUnrzGL.securityType == "REPO":
                repoDict['details'].append(tempDict)
        
        for cash in cashPositions:
            tempDict = {}
            tempDict['SecurityName'] = cash['Issuer']
            tempDict['totalrlzusd'] = cash['Pnl']
            tempDict['stgainloss'] = cash['Pnl']
            tempDict['ltgainloss'] = 0
            tempDict['Cost'] = '-'
            tempDict['Proceeds'] = '-'
            tempDict['intexp'] = '-'
            tempDict['intrev'] = '-'
            tempDict['Country'] = '-'
            tempDict['Currency'] = '-'
            tempDict['ISIN'] = ''
            cashDict['details'].append(tempDict)
        
        if len(bondDict['details']) > 0:
            unrzGlList.append(bondDict)
        if len(equityDict['details']) > 0:
            unrzGlList.append(equityDict)
        if len(futureDict['details']) > 0:
            unrzGlList.append(futureDict)
        if len(repoDict['details']) > 0:
            unrzGlList.append(repoDict)
        if len(optionDict['details']) > 0:
            unrzGlList.append(optionDict)
        if len(cdsDict['details']) > 0:
            unrzGlList.append(cdsDict)
        if len(cashDict['details']) > 0:
            unrzGlList.append(cashDict)

    ''' process the fuzzy search to dictionary '''
    def summaryofTransactionFuzzySearch(self,criteria):
        tradeList = g.dataBase.qFuzzyTradeHistory(criteria)
        fxTradeList = g.dataBase.qFuzzyTradeFx(criteria)
        resultList = []
        uniqueList = []
        
        for trans in tradeList:
            tempStr = trans.ISIN.encode('ascii') + trans.tranType.encode('ascii')
            #print(tempStr)
            if tempStr not in uniqueList:
                uniqueList.append(tempStr)
                tempList = {}
                tempList['ISIN'] = trans.ISIN.encode('ascii')
                tempList['securityName'] = trans.securityName.encode('ascii')
                tempList['securityType'] = trans.tranType.encode('ascii')
                tempList['volume'] = abs(trans.quantity)
                tempList['currency'] = trans.currType.encode('ascii')
                if trans.side == 'B':
                    tempList['intRevExp'] = -1*float(trans.accruedInt)
                else:
                    tempList['intRevExp'] = float(trans.accruedInt)
                tempList['realizedGL'] =0
                tempList['unrealizedGL'] = 0
                resultList.append(tempList)
            else:
                for item in resultList:
                    if item['ISIN']==trans.ISIN and item['securityType']==trans.tranType:
                        item['volume'] += abs(trans.quantity)
                        if trans.side == 'B':
                            item['intRevExp'] += -1*float(trans.accruedInt)
                        else:
                            item['intRevExp'] += float(trans.accruedInt)
        
        for item in resultList:
            #print(item['ISIN'])
            closeList=g.dataBase.qTradeCloseByISIN(item['ISIN'])
            openList = g.dataBase.qTradeHistoryByISIN(item['ISIN'],item['securityType'])
            tempSum = 0
            openQuantity = 0
            openCostBasis = 0
            for x in closeList:
                if x.tranType == item['securityType']:
                    if x.side1 == 'S':
                        tempSum += x.principalInUSD1 -  x.principalInUSD2
                    else:
                        tempSum += x.principalInUSD2 -  x.principalInUSD1
            item['realizedGL'] = float(tempSum)
            for y in openList:
                if y.reserve1 > 0 :
                    fxtemp = g.dataBase.qCurrencyByDate(y.currType,y.tradeDate)
                    if y.side == 'B':
                        openQuantity  += y.reserve1
                        openCostBasis += y.reserve1/y.quantity * y.principal*fxtemp[0].rate
                    else:
                        openQuantity  -= y.reserve1
                        openCostBasis -= y.reserve1/y.quantity * y.principal*fxtemp[0].rate

            if openQuantity != 0 :
                securityDetails = g.dataBase.qSecurityByISIN(item['ISIN'])
                print(item['ISIN'])
                print(openQuantity)
                print(openCostBasis)
                for z in securityDetails:
                    if z.securityType == item['securityType']:
                        securityPrice = z.currPrice
                        securityFactor = z.factor
                        fxQ = g.dataBase.qLatestCurrency(z.currType)
                        fxrate = fxQ[0].rate
                        if  item['securityType'] == 'EURO' : 
                            item['unrealizedGL'] = float(openQuantity*securityPrice*securityFactor*fxrate/100 - openCostBasis)
                        elif item['securityType'] == 'REPO':
                            item['unrealizedGL'] = 0
                        else:
                            item['unrealizedGL'] = float(openQuantity*securityPrice*securityFactor*fxrate - openCostBasis)
        print(resultList)
        return resultList
    
    '''computation of analytical topic'''
#    by jiahao: the positionList is positionListCategory
    def analyticCalculator(self, positionList):
#    analyticData stores all the topic as dict with data store under each key
        analyticData = {}
        analyticTopic = ['Bond Portfolio Duration', 'Sharpe Ratio monthly return', 'Bond Position annualized Volatility (1 month data)']       
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
                        try:
                            returnlist.append((pricelist[i+1]/pricelist[i])-1)
                        except:
                            print(ISIN)
                            print(pricelist)
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

        return analyticData
         
    ''' computation of portfolio carry'''
    def portforlioCarryComputation(self,positionList):
        totalCarry = 0
        for x in positionList:
            print(x['categoryName'])
            
            if x['categoryName'] == 'BOND':
                for y in x['details']:
                    if y['Category'] != 'BOND':
                        continue                    
                    if y['Currency'] == 'USD':
                        totalCarry += y['Quantity']* y['factor'] * y['Coupon']/100
                    else:
                        fxtemp = g.dataBase.qLatestCurrency(y['Currency'])
                        totalCarry += y['Quantity'] * y['factor'] * y['Coupon']*float(fxtemp[0].rate)/100
            elif x['categoryName'] == 'REPO':
                for y in x['details']:
                    if y['Currency'] == 'USD':
                        totalCarry += y['Quantity'] * y['Coupon']/100
                    else:
                        fxtemp = g.dataBase.qLatestCurrency(y['Currency'])
                        totalCarry += y['Quantity'] * y['Coupon']*float(fxtemp[0].rate)/100
            elif x['categoryName'] == 'CDS':
                for y in x['details']:
                    if y['Currency'] == 'USD':
                        totalCarry += y['Quantity'] * y['Coupon']/100
                    else:
                        fxtemp = g.dataBase.qLatestCurrency(y['Currency'])
                        totalCarry += y['Quantity'] * y['Coupon']*float(fxtemp[0].rate)/100
            elif x['categoryName'] =='EQTY':
                for y in x['details']:
                    if y['Currency'] == 'USD':
                        totalCarry += y['MarketValue'] * y['YTM']/100
                    else:
                        fxtemp = g.dataBase.qLatestCurrency(y['Currency'])
                        totalCarry += y['MarketValue'] * y['YTM']*float(fxtemp[0].rate)/100
        print(totalCarry)
        return totalCarry       
        
    ''' showing securities trending in portfolio'''
    def trendingData(self):
        securityList = g.dataBase.qSecurity()
        resultList = []
        bonddata=[]
        equitydata=[]
        derivativedata=[]
        
        
        for x in securityList:
            temp={}
            if x.securityType == 'REPO':
                continue
            priceList = g.dataBase.qPriceHistoryLastestThreeDays(x.ISIN)
            try:
                if (not all(priceList)) or len(priceList)<3:
                    continue
            except:
                print(priceList)
                print(x.ISIN)
            #print(priceList)
            
#             why we need encode
            temp['description'] = x.securityName.encode('ascii')
            temp['type'] = x.securityType.encode('ascii')
            temp['x'] =  round((float(priceList[0])/float(priceList[1])-1)*100,2)
            temp['y'] =  round((float(priceList[1])/float(priceList[2])-1)*100,2)
            if x.securityType == 'EURO':
                bonddata.append(temp)
            elif x.securityType =='EQTY':
                equitydata.append(temp)
            else:
                derivativedata.append(temp)
            
            resultList=[{
                'name':'Bond',
                'color':'rgba(223,83,83,0.8)',
                'data': bonddata
            },{
                'name':'Equity',
                'color':'rgba(69,102,141,0.8)',
                'data': equitydata        
            },{
                'name':'Derivatives',
                'color':'rgba(83,83,191,0.8)',
                'data': derivativedata
            }]
            
#         print(resultList)
        return resultList
        
        
            
        