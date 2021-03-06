# encoding: utf-8

import logging
'''
from vtFunction import AppLoger
apploger = AppLoger()
apploger.set_log_level(logging.INFO)
apiLog = apploger.get_logger()
'''

import json
import requests
from Queue import Queue, Empty
from threading import Thread


API_SETTING = {}
API_SETTING['practice'] = {'rest': 'https://api-fxpractice.oanda.com',
						   'stream': 'https://stream-fxpractice.oanda.com'}
API_SETTING['trade'] = {'rest': 'https://api-fxtrade.oanda.com',
						'stream': 'https://stream-fxtrade.oanda.com/'}


FUNCTIONCODE_GETINSTRUMENTS = 0
FUNCTIONCODE_GETPRICES = 1
FUNCTIONCODE_GETPRICEHISTORY = 2
FUNCTIONCODE_GETACCOUNTS = 3
FUNCTIONCODE_GETACCOUNTINFO = 4
FUNCTIONCODE_GETORDERS = 5
FUNCTIONCODE_SENDORDER = 6
FUNCTIONCODE_GETORDERINFO = 7
FUNCTIONCODE_MODIFYORDER = 8
FUNCTIONCODE_CANCELORDER = 9
FUNCTIONCODE_GETTRADES = 10
FUNCTIONCODE_GETTRADEINFO = 11
FUNCTIONCODE_MODIFYTRADE= 12
FUNCTIONCODE_CLOSETRADE = 13
FUNCTIONCODE_GETPOSITIONS = 14
FUNCTIONCODE_GETPOSITIONINFO= 15
FUNCTIONCODE_CLOSEPOSITION = 16
FUNCTIONCODE_GETTRANSACTIONS = 17
FUNCTIONCODE_GETTRANSACTIONINFO = 18
FUNCTIONCODE_GETACCOUNTHISTORY = 19
FUNCTIONCODE_GETCALENDAR = 20
FUNCTIONCODE_GETPOSITIONRATIOS = 21
FUNCTIONCODE_GETSPREADS = 22
FUNCTIONCODE_GETCOMMIMENTS = 23
FUNCTIONCODE_GETORDERBOOK = 24
FUNCTIONCODE_GETAUTOCHARTIST = 25
FUNCTIONCODE_STREAMPRICES = 26
FUNCTIONCODE_STREAMEVENTS = 27

from ctaAlgo.ctaParamLive import CTA_SETTING_LIST_LIVE

########################################################################
class OandaApiV3(object):
	""""""
	DEBUG = False

	#----------------------------------------------------------------------
	def __init__(self):
		"""Constructor"""
		
		self.logger = logging.getLogger(__name__)
		self.logger.debug("OandaApi.logger inited")

		self.token = ''
		self.accountId = ''
		self.headers = {}
		self.restDomain = ''
		self.streamDomain = ''
		self.session = None
		self.orderInstrument=['USD_JPY']

		self.functionSetting = {}
		
		self.active = False         # API的工作状态
		
		self.reqID = 0              # 请求编号
		self.reqQueue = Queue()     # 请求队列
		self.reqThread = Thread(target=self.processQueue)   # 请求处理线程
		
		self.symbols = [x['vtSymbol'] for x in CTA_SETTING_LIST_LIVE] # AUG02
		
		self.streamPricesThread = Thread(target=self.processStreamPrices)   # 实时行情线程
		self.streamEventsThread = Thread(target=self.processStreamEvents)   # 实时事件线程（成交等）
		
	#----------------------------------------------------------------------
	def init(self, settingName, token, accountId):
		"""初始化接口"""
		self.restDomain = API_SETTING[settingName]['rest']
		self.streamDomain = API_SETTING[settingName]['stream']
		self.session = requests.Session()
		
		self.token = token
		self.accountId = accountId
		
		self.headers['Authorization'] = 'Bearer ' + self.token
		
		self.initFunctionSetting(FUNCTIONCODE_GETINSTRUMENTS, {'path': '/v3/accounts/%s/instruments' % self.accountId,
														  'method': 'GET'})
		
		self.initFunctionSetting(FUNCTIONCODE_GETPRICES, {'path': '/v3/accounts/%s/pricing' % self.accountId,
														  'method': 'GET'})        
		
		self.initFunctionSetting(FUNCTIONCODE_GETPRICEHISTORY, {'path': '/v3/candles',
																'method': 'GET'})
		
		self.initFunctionSetting(FUNCTIONCODE_GETACCOUNTS, {'path': '/v3/accounts',
														  'method': 'GET'})  
		
		self.initFunctionSetting(FUNCTIONCODE_GETACCOUNTINFO, {'path': '/v3/accounts/%s/summary' %self.accountId,
														  'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETORDERS, {'path': '/v3/accounts/%s/orders' %self.accountId,
														  'method': 'GET'})        
		
		self.initFunctionSetting(FUNCTIONCODE_SENDORDER, {'path': '/v3/accounts/%s/orders' %self.accountId,
														  'method': 'POST'})     
		
		self.initFunctionSetting(FUNCTIONCODE_GETORDERINFO, {'path': '/v3/accounts/%s/orders' %self.accountId,
														  'method': 'GET'})     
		
		self.initFunctionSetting(FUNCTIONCODE_MODIFYORDER, {'path': '/v3/accounts/%s/orders' %self.accountId,
														  'method': 'PATCH'})    
		
		self.initFunctionSetting(FUNCTIONCODE_CANCELORDER, {'path': '/v3/accounts/%s/orders' %self.accountId,
														  'method': 'DELETE'})             
		
		self.initFunctionSetting(FUNCTIONCODE_GETTRADES, {'path': '/v3/accounts/%s/trades' %self.accountId,
														  'method': 'GET'})        

		self.initFunctionSetting(FUNCTIONCODE_GETTRADEINFO, {'path': '/v3/accounts/%s/trades' %self.accountId,
															 'method': 'GET'})     
		
		self.initFunctionSetting(FUNCTIONCODE_MODIFYTRADE, {'path': '/v3/accounts/%s/trades' %self.accountId,
															'method': 'PATCH'})    
		
		self.initFunctionSetting(FUNCTIONCODE_CLOSETRADE, {'path': '/v3/accounts/%s/trades' %self.accountId,
														   'method': 'DELETE'})     
		
		self.initFunctionSetting(FUNCTIONCODE_GETPOSITIONS, {'path': '/v3/accounts/%s/openPositions' %self.accountId,
															 'method': 'GET'})     
		
		self.initFunctionSetting(FUNCTIONCODE_GETPOSITIONINFO, {'path': '/v3/accounts/%s/positions' %self.accountId,
																'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_CLOSEPOSITION, {'path': '/v3/accounts/%s/positions' %self.accountId,
															  'method': 'DELETE'})            
		
		self.initFunctionSetting(FUNCTIONCODE_GETTRANSACTIONS, {'path': '/v3/accounts/%s/transactions' %self.accountId,
																'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETTRANSACTIONINFO, {'path': '/v3/accounts/%s/transactions' %self.accountId,
																   'method': 'GET'})    
		# v20,v1 rest都没有历史账户的功能
		self.initFunctionSetting(FUNCTIONCODE_GETACCOUNTHISTORY, {'path': '/v3/accounts/%s/alltransactions' %self.accountId,
																  'method': 'GET'})     
		
		self.initFunctionSetting(FUNCTIONCODE_GETCALENDAR, {'path': '/labs/v1/calendar',
															'method': 'GET'})           
		
		self.initFunctionSetting(FUNCTIONCODE_GETPOSITIONRATIOS, {'path': '/labs/v3/historical_position_ratios',
																  'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETSPREADS, {'path': '/labs/v3/spreads',
														   'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETCOMMIMENTS, {'path': '/labs/v3/commitments',
															  'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETORDERBOOK, {'path': '/labs/v3/orderbook_data',
															 'method': 'GET'})    
		
		self.initFunctionSetting(FUNCTIONCODE_GETAUTOCHARTIST, {'path': '/labs/v3/autochartist',
																'method': 'GET'})  
		
		self.initFunctionSetting(FUNCTIONCODE_GETAUTOCHARTIST, {'path': '/labs/v3/autochartist',
																'method': 'GET'})  
		
		self.initFunctionSetting(FUNCTIONCODE_STREAMPRICES, {'path': '/v3/accounts/%s/pricing/stream' % self.accountId,
															 'method': 'GET'})  
		# v20 transaction stream
		self.initFunctionSetting(FUNCTIONCODE_STREAMEVENTS, {'path': '/v3/accounts/%s/transactions/stream' % self.accountId,
															 'method': 'GET'})          
		
		
		self.active = True
		self.reqThread.start()
		self.streamEventsThread.start()
		self.streamPricesThread.start()
		
	#----------------------------------------------------------------------
	def exit(self):
		"""退出接口"""
		if self.active:
			self.active = False
			self.reqThread.join()
		
	#----------------------------------------------------------------------
	def initFunctionSetting(self, code, setting):
		"""初始化API功能字典"""
		self.functionSetting[code] = setting
		
	#----------------------------------------------------------------------
	def processRequest(self, req):
		"""发送请求并通过回调函数推送数据结果"""
		url = req['url']
		method = req['method']
		params = req['params']
		
		stream = False
		if 'stream' in req:
			stream = req['stream']

		if method in ['GET', 'DELETE']:
			myreq = requests.Request(method, url, headers=self.headers, params=params)
		elif method in ['POST', 'PATCH']:
			myreq = requests.Request(method, url, headers=self.headers, data=params)
		pre = myreq.prepare()
		self.logger.info("method:%s, head:%s, will send url:%s, params:%s" % (method, pre.headers, pre.url, params))

		r = None
		error = None
		
		try:
			r = self.session.send(pre, stream=stream)
		except Exception, e:
			error = e
		if r != None: 
			self.logger.info("response is %s, error is %s" % (r.json(), error))
	
		return r, error
	
	#----------------------------------------------------------------------
	def processQueue(self):
		"""处理请求队列中的请求"""
		while self.active:
			try:
				req = self.reqQueue.get(block=True, timeout=1)  # 获取请求的阻塞为一秒
				callback = req['callback']
				reqID = req['reqID']
				
				#oanda返回消息
				r, error = self.processRequest(req)
				self.logger.info("callback is %s, reqID:%d" % (callback.__name__, reqID))
				if r:
					try:
						#提取返回消息的body
						data = r.json()
						if self.DEBUG:
							print callback.__name__                        
						callback(data, reqID)    
					except Exception, e:                  
						self.onError(str(e), reqID)
						self.logger.error("callback %s exception %s" %(callback.__name__, str(e)))                      
				else:                
					self.onError(error, reqID)
			except Empty:
				pass
			
	#----------------------------------------------------------------------
	def sendRequest(self, code, params, callback, optional=''):
		"""发送请求"""
		setting = self.functionSetting[code]
		
		url = self.restDomain + setting['path']
		if optional:
			url = url + '/' + optional
			
		self.reqID += 1
			
		req = {'url': url,
			   'method': setting['method'],
			   'params': params,
			   'callback': callback,
			   'reqID': self.reqID}
		self.reqQueue.put(req)
		
		self.logger.info("send url:%s, method:%s, params:%s, reqID:%d" % (url, setting['method'], params, self.reqID))
		return self.reqID
	
	#----------------------------------------------------------------------
	def onError(self, error, reqID):
		"""错误信息回调"""
		print error, reqID
			
	#----------------------------------------------------------------------
	def getInstruments(self, params):
		"""查询可交易的合约列表"""
		return self.sendRequest(FUNCTIONCODE_GETINSTRUMENTS, params, self.onGetInstruments)
		
	#----------------------------------------------------------------------
	def onGetInstruments(self, data, reqID):
		"""回调函数"""
		pass
		
	#----------------------------------------------------------------------
	def getPrices(self, params):
		"""查询价格"""
		return self.sendRequest(FUNCTIONCODE_GETPRICES, params, self.onGetPrices)
		
	#----------------------------------------------------------------------
	def onGetPrices(self, data, reqID):
		"""回调函数"""
		pass
		
	#----------------------------------------------------------------------
	def getPriceHisory(self, params):
		"""查询历史价格数据"""
		return self.sendRequest(FUNCTIONCODE_GETPRICEHISTORY, params, self.onGetPriceHistory)
		
	#----------------------------------------------------------------------
	def onGetPriceHistory(self, data, reqID):
		"""回调函数"""
		pass    
		
	#----------------------------------------------------------------------
	def getAccounts(self):
		"""查询用户的所有账户"""
		return self.sendRequest(FUNCTIONCODE_GETACCOUNTS, {}, self.onGetAccounts)
	
	#----------------------------------------------------------------------
	def onGetAccounts(self, data, reqID):
		"""回调函数"""
		pass   
		
	#----------------------------------------------------------------------
	def getAccountInfo(self):
		"""查询账户数据"""
		return self.sendRequest(FUNCTIONCODE_GETACCOUNTINFO, {}, self.onGetAccountInfo)
	
	#----------------------------------------------------------------------
	def onGetAccountInfo(self, data, reqID):
		"""回调函数"""
		pass   
		
	#----------------------------------------------------------------------
	def getOrders(self, params):
		"""查询所有委托"""
		return self.sendRequest(FUNCTIONCODE_GETORDERS, params, self.onGetOrders)
	
	#----------------------------------------------------------------------
	def onGetOrders(self, data, reqID):
		"""回调函数"""
		pass     

	#----------------------------------------------------------------------
	def sendOrder(self, params):
		"""发送委托"""
		return self.sendRequest(FUNCTIONCODE_SENDORDER, params, self.onSendOrder)
	
	#----------------------------------------------------------------------
	def onSendOrder(self, data, reqID):
		"""回调函数"""
		pass         
	
	#----------------------------------------------------------------------
	def getOrderInfo(self, optional):
		"""查询委托信息"""
		return self.sendRequest(FUNCTIONCODE_GETORDERINFO, {}, self.onGetOrderInfo, optional)
	
	#----------------------------------------------------------------------
	def onGetOrderInfo(self, data, reqID):
		"""回调函数"""
		pass     
		
	#----------------------------------------------------------------------
	def modifyOrder(self, params, optional):
		"""修改委托"""
		return self.sendRequest(FUNCTIONCODE_MODIFYORDER, params, self.onModifyOrder, optional)
	
	#----------------------------------------------------------------------
	def onModifyOrder(self, data, reqID):
		"""回调函数"""
		pass      
	
	#----------------------------------------------------------------------
	def cancelOrder(self, optional):
		"""查询委托信息"""
		return self.sendRequest(FUNCTIONCODE_CANCELORDER, {}, self.onCancelOrder, optional)
	
	#----------------------------------------------------------------------
	def onCancelOrder(self, data, reqID):
		"""回调函数"""
		pass     
	
	#----------------------------------------------------------------------
	def getTrades(self, params):
		"""查询所有仓位"""
		return self.sendRequest(FUNCTIONCODE_GETTRADES, params, self.onGetTrades)
	
	#----------------------------------------------------------------------
	def onGetTrades(self, data, reqID):
		"""回调函数"""
		pass     
	
	#----------------------------------------------------------------------
	def getTradeInfo(self, optional):
		"""查询仓位信息"""
		return self.sendRequest(FUNCTIONCODE_GETTRADEINFO, {}, self.onGetTradeInfo, optional)
	
	#----------------------------------------------------------------------
	def onGetTradeInfo(self, data, reqID):
		"""回调函数"""
		pass     
		
	#----------------------------------------------------------------------
	def modifyTrade(self, params, optional):
		"""修改仓位"""
		return self.sendRequest(FUNCTIONCODE_MODIFYTRADE, params, self.onModifyTrade, optional)
	
	#----------------------------------------------------------------------
	def onModifyTrade(self, data, reqID):
		"""回调函数"""
		pass      
	
	#----------------------------------------------------------------------
	def closeTrade(self, optional):
		"""平仓"""
		return self.sendRequest(FUNCTIONCODE_CLOSETRADE, {}, self.onCloseTrade, optional)
	
	#----------------------------------------------------------------------
	def onCloseTrade(self, data, reqID):
		"""回调函数"""
		pass         

	#----------------------------------------------------------------------
	def getPositions(self):
		"""查询所有汇总仓位"""
		return self.sendRequest(FUNCTIONCODE_GETPOSITIONS, {}, self.onGetPositions)
	
	#----------------------------------------------------------------------
	def onGetPositions(self, data, reqID):
		"""回调函数"""
		pass  
		
	#----------------------------------------------------------------------
	def getPositionInfo(self, optional):
		"""查询汇总仓位信息"""
		return self.sendRequest(FUNCTIONCODE_GETPOSITIONINFO, {}, self.onGetPositionInfo, optional)
	
	#----------------------------------------------------------------------
	def onGetPositionInfo(self, data, reqID):
		"""回调函数"""
		pass         

	#----------------------------------------------------------------------
	def closePosition(self, optional):
		"""平仓汇总仓位信息"""
		return self.sendRequest(FUNCTIONCODE_CLOSEPOSITION, {}, self.onClosePosition, optional)
	
	#----------------------------------------------------------------------
	def onClosePosition(self, data, reqID):
		"""回调函数"""
		pass      
	
	
	#----------------------------------------------------------------------
	def getTransactions(self, params):
		"""查询所有资金变动"""
		return self.sendRequest(FUNCTIONCODE_GETTRANSACTIONS, params, self.onGetTransactions)
	
	#----------------------------------------------------------------------
	def onGetTransactions(self, data, reqID):
		"""回调函数"""
		pass  
		
	#----------------------------------------------------------------------
	def getTransactionInfo(self, optional):
		# print ("enter getTransactionInfo %s" % optional)
		"""查询资金变动信息"""
		return self.sendRequest(FUNCTIONCODE_GETTRANSACTIONINFO, {}, self.onGetTransactionInfo, optional)
	
	#----------------------------------------------------------------------
	def onGetTransactionInfo(self, data, reqID):
		"""回调函数"""
		pass   
		
	#----------------------------------------------------------------------
	def getAccountHistory(self):
		"""查询账户资金变动历史"""
		return self.sendRequest(FUNCTIONCODE_GETACCOUNTHISTORY, {}, self.onGetAccountHistory)
	
	#----------------------------------------------------------------------
	def onGetAccountHistory(self, data, reqID):
		"""回调函数"""
		pass      
	
	#----------------------------------------------------------------------
	def getCalendar(self, params):
		"""查询日历"""
		return self.sendRequest(FUNCTIONCODE_GETCALENDAR, params, self.onGetCalendar)
	
	#----------------------------------------------------------------------
	def onGetCalendar(self, data, reqID):
		"""回调函数"""
		pass       
		
	#----------------------------------------------------------------------
	def getPositionRatios(self, params):
		"""查询持仓比例"""
		return self.sendRequest(FUNCTIONCODE_GETPOSITIONRATIOS, params, self.onGetPositionRatios)
	
	#----------------------------------------------------------------------
	def onGetPositionRatios(self, data, reqID):
		"""回调函数"""
		pass  
		
	#----------------------------------------------------------------------
	def getSpreads(self, params):
		"""查询所有仓位"""
		return self.sendRequest(FUNCTIONCODE_GETSPREADS, params, self.onGetSpreads)
	
	#----------------------------------------------------------------------
	def onGetSpreads(self, data, reqID):
		"""回调函数"""
		pass       
		
	#----------------------------------------------------------------------
	def getCommitments(self, params):
		"""查询交易商持仓情况"""
		return self.sendRequest(FUNCTIONCODE_GETCOMMIMENTS, params, self.onGetCommitments)
	
	#----------------------------------------------------------------------
	def onGetCommitments(self, data, reqID):
		"""回调函数"""
		pass       
	
	#----------------------------------------------------------------------
	def getOrderbook(self, params):
		"""查询订单簿"""
		return self.sendRequest(FUNCTIONCODE_GETORDERBOOK, params, self.onGetOrderbook)
	
	#----------------------------------------------------------------------
	def onGetOrderbook(self, data, reqID):
		"""回调函数"""
		pass       
		
	#----------------------------------------------------------------------
	def getAutochartist(self, params):
		"""查询Autochartist识别的模式"""
		return self.sendRequest(FUNCTIONCODE_GETAUTOCHARTIST, params, self.onGetAutochartist)
	
	#----------------------------------------------------------------------
	def onGetAutochartist(self, data, reqID):
		"""回调函数"""
		pass   
		
	#----------------------------------------------------------------------
	def onPrice(self, data):
		"""行情推送"""
		print data
		
	#----------------------------------------------------------------------
	def onEvent(self, data):
		"""事件推送（成交等）"""
		print data
		
	#----------------------------------------------------------------------
	def processStreamPrices(self):
		"""获取价格推送"""
		# 首先获取所有合约的代码
		setting = self.functionSetting[FUNCTIONCODE_GETORDERS]
		req = {'url': self.restDomain + setting['path'],
			   'method': setting['method'],
			   'params': {}}
		r, error = self.processRequest(req)
		if r:
			try:
				data = r.json()
				# v20 api 没有instrument字段
				# symbols = [d['name'] for d in data['instruments']]
				l = data['orders']
				for d in l:
					if not 'instrument'in d and not d['instrument'] in self.orderInstrument:
						self.orderInstrument.append(d['instrument'])

				self.logger.info("get instrument name %s" % self.orderInstrument)   
			except Exception, e:
				self.onError(e, -1)
				self.logger.error("get instruments error %s" % e)
				return
		else:
			self.onError(error, -1)
			return

		# 然后订阅所有的合约行情
		setting = self.functionSetting[FUNCTIONCODE_STREAMPRICES]
		# params = {'accountId': self.accountId,
		#           'instruments': ','.join(self.orderInstrument)}
		params = {'instruments':','.join(self.orderInstrument)}
		# params = {'instruments': self.orderInstrument[0]}

		req = {'url': self.streamDomain + setting['path'],
			   'method': setting['method'],
			   'params': params,
			   'stream': True}    
	   
		# r, error = self.processRequest(req)

		myreq = requests.Request(req['method'], req['url'], headers=self.headers, params=req['params'])
		pre = myreq.prepare()

		s = requests.session()
		r = s.send(pre, stream=True)
		
		if r:
			for line in r.iter_lines():
				if line:
					try:
						msg = json.loads(line)
						
						if self.DEBUG:
							print self.onPrice.__name__
						self.logger.info("get price %s" % msg)
						self.onPrice(msg)
					except Exception, e:
						self.onError(e, -1)
				
				if not self.active:
					break
		else:
			self.onError(error, -1)
	
	#----------------------------------------------------------------------
	def processStreamEvents(self):
		"""获取事件推送"""
		setting = self.functionSetting[FUNCTIONCODE_STREAMEVENTS]
		req = {'url': self.streamDomain + setting['path'],
			   'method': setting['method'],
			   'params': {},
			   'stream': True}
		# r, error = self.processRequest(req)

		myreq = requests.Request(req['method'], req['url'], headers=self.headers, params=req['params'])
		pre = myreq.prepare()

		s = requests.session()
		r = s.send(pre, stream=True)
		
		if r:
			for line in r.iter_lines():
				if line:
					try:
						msg = json.loads(line)
						
						if self.DEBUG:
							print self.onEvent.__name__
							
						self.onEvent(msg)
					except Exception, e:
						self.onError(e, -1)
				
				if not self.active:
					break
		else:
			self.onError(error, -1)