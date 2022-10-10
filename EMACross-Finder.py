from asyncio.windows_events import NULL
from cmath import nan
from fileinput import close, filename
import math
from operator import truediv
import os
from pydoc import doc
from re import I
from turtle import down
from backtesting import Backtest, Strategy
from backtesting.test import SMA
import talib
from backtesting.lib import SignalStrategy,TrailingStrategy

from numbers import Number
from typing import Sequence
import pandas as pd

currDir = os.getcwd()

#Enter candlestick data here
fileName = r"\XAUUSD_M5_2W.csv"
fullPath = currDir + fileName

dataframe = pd.read_csv(fullPath, 
                     names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Orders'], 
                     index_col='Date_Time', parse_dates=[[0, 1]])

def crossUp(series1: Sequence, series2: Sequence) -> bool:
    series1 = (
        series1.values if isinstance(series1, pd.Series) else
        (series1, series1) if isinstance(series1, Number) else
        series1)
    series2 = (
        series2.values if isinstance(series2, pd.Series) else
        (series2, series2) if isinstance(series2, Number) else
        series2)
    try:
        if series1[-1] > series2[-1] and series1[-5] < series2[-5]:
            slope = (series1[-1] - series1[-4]) / 2

            threshDist = _Point(dataframe['Close'][0]) * 10

            if slope > threshDist:
                return True

        return False
    except IndexError:
        return False


def crossDown(series1: Sequence, series2: Sequence) -> bool:
    series1 = (
        series1.values if isinstance(series1, pd.Series) else
        (series1, series1) if isinstance(series1, Number) else
        series1)
    series2 = (
        series2.values if isinstance(series2, pd.Series) else
        (series2, series2) if isinstance(series2, Number) else
        series2)
    try:
        if series1[-1] < series2[-1] and series1[-5] > series2[-5]:
            slope = (series1[-1] - series1[-4]) / 2

            threshDist = -1 * _Point(dataframe['Close'][0]) * 10

            if slope < threshDist:
                return True

        return False
    except IndexError:
        return False


CANDLE_LOOP_COUNT = 70

def getPrevLow(wickArray):

    lowest = wickArray[-2]

    #loop candles
    for i in range(2, CANDLE_LOOP_COUNT):
       if lowest > wickArray[len(wickArray) - i]:
            lowest = wickArray[len(wickArray) - i]

    #if current candle is the lowest
    if wickArray[-1] < lowest:
        return 0

    return lowest

def getPrevHigh(wickArray):
    highest = wickArray[-2]
    highestIndex = 0

    #loop candles
    for i in range(2, CANDLE_LOOP_COUNT):
       if highest < wickArray[len(wickArray) - i]:
            highestIndex = len(wickArray) - i
            highest = wickArray[len(wickArray) - i]

    return highest


def _Point(num):
    numLen = len(str(num).split('.')[-1])
    pointNum = 10 ** (-1 * numLen)
    return pointNum


TREND_CANDLE_COUNT = 150

def isDownTrend(largeEMA):
    if len(largeEMA) < TREND_CANDLE_COUNT + 14:
        return False

    distance = (largeEMA[-1] - largeEMA[-14]) 

    if distance > 0:
        return False


    largeDist = _Point(dataframe['Close'][0]) * 30

    if abs(distance) > largeDist:
        return True
    return False


def isUpTrend(largeEMA):
    if len(largeEMA) < TREND_CANDLE_COUNT + 14:
        return False

    distance = (largeEMA[-1] - largeEMA[-14]) 

    if distance < 0:
        return False


    largeDist = _Point(dataframe['Close'][0]) * 30

    if distance > largeDist:
        return True
    return False


targetHigh = 0
targetLow = 0

reversalWait = 0

def detectReversal(smallEMA, trendEMA):
    #check if smallEMA has crossed a "large" distance in opposite direction of trend
    if isUpTrend(trendEMA):
        distance = (smallEMA[-1] - smallEMA[-14])
        #opposite to check for reversal
        if distance < 0:
            largeDist = _Point(dataframe['Close'][0]) * 30
            if abs(distance) > largeDist:
                return True

    elif isDownTrend(trendEMA):
        distance = (smallEMA[-1] - smallEMA[-14])
        if distance > 0:
            largeDist = _Point(dataframe['Close'][0]) * 30
            if abs(distance) > largeDist:
                return True
    

    return False

IN_TRADE = 0
TRADE_SKIPS = 0

EMA_NUM = 20
EMA_NUM2 = 50

class BollingerReversal(SignalStrategy):
    def init(self):
        super().init()

        price = self.data.Close
        #self.trendSMA = self.I(SMA, price, TREND_CANDLE_COUNT)
        self.SMA1 = self.I(SMA, price, EMA_NUM)
        self.SMA2 = self.I(SMA, price, EMA_NUM2)
        #self.EXITSMA = self.I(SMA, price, 13)

    def next(self):
        global reversalWait, targetHigh, targetLow, IN_TRADE, TRADE_SKIPS
        #on each candle
        price = self.data.Close[-1]

        if len(self.data.Close) == 998:
            a = 1 - 1

        if TRADE_SKIPS > 0:
            TRADE_SKIPS -= 1
            return

        if IN_TRADE:
            if len(self.trades) > 0:
                percentDiff = self.trades[-1].pl_pct
                percentDiff /= _Point(dataframe['Close'][0])

                if percentDiff < -0.07:
                    self.trades[-1].close()
                    IN_TRADE = 0
                    TRADE_SKIPS = 20
                    return

                #enter and exit rules here
                if self.trades[0].is_long:
                    if crossDown(self.SMA1, self.SMA2):
                        if self.trades[0].pl < 0:
                            TRADE_SKIPS = 20
                        
                        self.trades[0].close()
                        IN_TRADE = 0
                
                elif self.trades[0].is_short:
                    if crossUp(self.SMA1, self.SMA2):
                        if self.trades[0].pl < 0:
                            TRADE_SKIPS = 20
                        self.trades[0].close()
                        IN_TRADE = 0

            return

        #if isUpTrend(self.trendSMA):
        if crossUp(self.SMA1, self.SMA2):
            self.buy()
            IN_TRADE = 1

       # elif isDownTrend(self.trendSMA):
        elif crossDown(self.SMA1, self.SMA2):
            self.sell()
            IN_TRADE = 1



            
            
        return


profitFactorList = []

biggestProfit = 0




for i in range(5, 101, 5):
    for j in range(5, 201, 5):
        if abs(i - j) < 11:
            continue

        IN_TRADE = 0
        TRADE_SKIPS = 0

        EMA_NUM = i
        EMA_NUM2 = j

        calcCommision = 0

        bt = Backtest(dataframe, BollingerReversal, commission=calcCommision,
                    exclusive_orders=True, cash=100 * 30, margin=0.01, trade_on_close=False)

        stats = bt.run()

        if stats['Profit Factor'] > biggestProfit:
            if i < j:
                biggestProfit = stats['Profit Factor']
                print("New best: " + str(biggestProfit) + ", i: " + str(i) + ", j: " + str(j))
                print("")
                profitFactorList.append([stats['Profit Factor'], i, j])
        




print("Top 5 Profit Factors:\n")

if len(profitFactorList) > 5:
    for i in range(5):
        print(str(i + 1) + ") " + str(profitFactorList[len(profitFactorList) - i - 1]))

else :
    for i in range(len(profitFactorList)):
        print(str(i + 1) + ") " + profitFactorList[len(profitFactorList) - i])

