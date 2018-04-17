

########################################################################
class Api(OandaApi):
    """OANDA的API实现"""

    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(Api, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.orderDict = {}     # 缓存委托数据
        
    #----------------------------------------------------------------------
    def onError(self, error, reqID):
        """错误信息回调"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorMsg = error
        self.gateway.onError(err)

    #----------------------------------------------------------------------
    def onGetInstruments(self, data, reqID):
        """回调函数"""
        if not 'instruments' in data:
            return
        l = data['instruments']
        for d in l:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName
            
            contract.symbol = d['instrument']
            contract.name = d['displayName']
            contract.exchange = EXCHANGE_OANDA
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            contract.priceTick = float(d['pip'])
            contract.size = 1
            contract.productClass = PRODUCT_FOREX
            self.gateway.onContract(contract)
        
        self.writeLog(u'交易合约信息查询完成')

    #----------------------------------------------------------------------
    def onGetAccountInfo(self, data, reqID):
        """回调函数"""
        account = VtAccountData()
        account.gatewayName = self.gatewayName
        
        account.accountID = str(data['accountId'])
        account.vtAccountID = '.'.join([self.gatewayName, account.accountID])
        
        account.available = data['marginAvail']
        account.margin = data['marginUsed']
        account.closeProfit = data['realizedPl']
        account.positionProfit = data['unrealizedPl']
        account.balance = data['balance']
        
        self.gateway.onAccount(account)
        
    #----------------------------------------------------------------------
    def onGetOrders(self, data, reqID):
        """回调函数"""
        if not 'orders' in data:
            return
        l = data['orders']  
        
        for d in l:
            order = VtOrderData()
            order.gatewayName = self.gatewayName
            
            order.symbol = d['instrument']
            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])
            
            order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED     # OANDA查询到的订单都是活动委托
            
            order.price = d['price']
            order.totalVolume = d['units']
            order.orderTime = getTime(d['time'])
            
            order.vtOrderID = '.'.join([self.gatewayName , order.orderID])
            
            self.gateway.onOrder(order)
            
            self.orderDict[order.orderID] = order
            
        self.writeLog(u'委托信息查询完成')
    
    #----------------------------------------------------------------------
    def onGetPositions(self, data, reqID):
        """回调函数"""
        if not 'positions' in data:
            return
        l = data['positions']
        
        for d in l:
            pos = VtPositionData()
            pos.gatewayName = self.gatewayName
            
            pos.symbol = d['instrument']
            pos.exchange = EXCHANGE_OANDA
            pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
            pos.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            pos.position = d['units']
            pos.price = d['avgPrice']
            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])
            
            self.gateway.onPosition(pos)

    #----------------------------------------------------------------------
    def onGetTransactions(self, data, reqID):
        """回调函数"""
        if not 'transactions' in data:
            return
        l = data['transactions']
        
        for d in l:
            # 这里我们只关心委托成交
            if d['type'] == 'ORDER_FILLED':
                trade = VtTradeData()
                trade.gatewayName = self.gatewayName
                
                trade.symbol = d['instrument']
                trade.exchange = EXCHANGE_OANDA
                trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
                trade.tradeID = str(d['id'])
                trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
                trade.orderID = str(d['orderId'])
                trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])                 
                trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
                trade.offset = OFFSET_NONE
                trade.price = d['price']
                trade.volume = d['units']
                trade.tradeTime = getTime(d['time'])
                
                self.gateway.onTrade(trade)
                
        self.writeLog(u'成交信息查询完成')
        
    #----------------------------------------------------------------------
    def onPrice(self, data):
        """行情推送"""
        if 'tick' not in data:
            return
        d = data['tick']
        
        tick = VtTickData()
        tick.gatewayName = self.gatewayName
    
        tick.symbol = d['instrument']
        tick.exchange = EXCHANGE_OANDA
        tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])    
        tick.bidPrice1 = d['bid']
        tick.askPrice1 = d['ask']
        tick.time = getTime(d['time'])
        
        # 做市商的TICK数据只有买卖的报价，因此最新价格选用中间价代替
        tick.lastPrice = (tick.bidPrice1 + tick.askPrice1)/2        
        agentLog.info("tick is %s " % tick)
        self.gateway.onTick(tick)
        
    #----------------------------------------------------------------------
    def onEvent(self, data):
        """事件推送（成交等）"""
        if 'transaction' not in data:
            return
        
        d = data['transaction']
        
        # 委托成交
        if d['type'] == 'ORDER_FILLED':
            # 推送成交事件
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
            
            trade.symbol = d['instrument']
            trade.exchange = EXCHANGE_OANDA
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
            
            trade.tradeID = str(d['id'])
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
            
            trade.orderID = str(d['orderId'])
            trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])                    

            trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            trade.offset = OFFSET_NONE
            
            trade.price = d['price']
            trade.volume = d['units']
            trade.tradeTime = getTime(d['time'])
            
            self.gateway.onTrade(trade)      
            
            # 推送委托事件
            order = self.orderDict.get(str(d['orderId']), None)
            if not order:
                return
            order.status = STATUS_ALLTRADED
            self.gateway.onOrder(order)             
        
        # 委托下达
        elif d['type'] in ['MARKET_ORDER_CREATE', 'LIMIT_ORDER_CREATE']:
            order = VtOrderData()
            order.gatewayName = self.gatewayName
    
            order.symbol = d['instrument']
            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])
            order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED    
            order.price = d['price']
            order.totalVolume = d['units']
            order.orderTime = getTime(d['time'])
            order.vtOrderID = '.'.join([self.gatewayName , order.orderID])
    
            self.gateway.onOrder(order)   
            self.orderDict[order.orderID] = order
            
        # 委托撤销
        elif d['type'] == 'ORDER_CANCEL':
            order = self.orderDict.get(str(d['orderId']), None)
            if not order:
                return
            order.status = STATUS_CANCELLED
            self.gateway.onOrder(order)
    
    #----------------------------------------------------------------------
    def writeLog(self, logContent):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = logContent
        self.gateway.onLog(log)
        
    #----------------------------------------------------------------------
    def qryInstruments(self):
        """查询合约"""
        params = {'accountId': self.accountId}
        self.getInstruments(params)
        
    #----------------------------------------------------------------------
    def qryOrders(self):
        """查询委托"""
        self.getOrders({})
        
    #----------------------------------------------------------------------
    def qryTrades(self):
        """查询成交"""
        # 最多查询100条记录
        self.getTransactions({'count': 100})
        
    #----------------------------------------------------------------------
    def sendOrder_(self, orderReq):
        """发送委托"""
        params = {}
        params['instrument'] = orderReq.symbol
        params['units'] = orderReq.volume
        params['side'] = directionMap.get(orderReq.direction, '')
        params['price'] = orderReq.price
        params['type'] = priceTypeMap.get(orderReq.priceType, '')
        
        # 委托有效期24小时
        expire = datetime.datetime.now() + datetime.timedelta(days=1)
        params['expiry'] = expire.isoformat('T') + 'Z'
        
        self.sendOrder(params)
    
    #----------------------------------------------------------------------
    def cancelOrder_(self, cancelOrderReq):
        """撤销委托"""
        self.cancelOrder(cancelOrderReq.orderID)
    
    
#----------------------------------------------------------------------
def getTime(t):
    """把OANDA返回的时间格式转化为简单的时间字符串"""
    return t[11:19]


