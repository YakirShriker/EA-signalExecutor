import MetaTrader5 as mt5
import time

# Global variables
global testing
testing = True
global reached_tp_already
reached_tp_already = True
# Dictionaries to store pending orders and active orders
orders_dict = {"pending_orders": {}, "active_orders": {}}


# Function to send pending orders and store them in memory
def send_order(symbol, order_type, price, sl, tp, lot, magic_number):
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": magic_number,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Order placed: {symbol}, {order_type}, Price: {price}, Lot: {lot}, SL: {sl}, TP: {tp}")
        # Store the order in memory

        orders_dict["pending_orders"][symbol][result.order] = {
            "symbol": symbol,
            "order_type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "lot": lot,
            "magic": magic_number,
            "tripled": False
        }
        return result.order  # Return the order ID
    else:
        print(f"Failed to place {symbol} order: {result.comment}")
        return None

# Function to delete a pending order
def delete_order(order_id):
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": order_id
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Order {order_id} successfully deleted")
    else:
        print(f"Failed to delete order {order_id}: {result.comment}")

def remove_all_orders_per_pair(symbol):
    for order_id in list(orders_dict["pending_orders"][symbol].keys()):
        delete_order(order_id)
    del orders_dict["pending_orders"][symbol]

def check_tp(symbol):
    current_price = mt5.symbol_info_tick(symbol).bid
    for order_id in list(orders_dict["pending_orders"][symbol].keys()):
        order_info = orders_dict["pending_orders"][symbol][order_id]
        print(f"current price {current_price} and TP {order_info['tp']} and order type {order_info['order_type']}")
        if order_info["order_type"] == 4 or order_info["order_type"] == 2:
            if current_price >= order_info["tp"]:
                print(f"Order {order_id} is BUY and reached TP before started")
                remove_all_orders_per_pair(symbol)
                return False
            else:
                print(f"Order {order_id} is buy and ok")
        if order_info["order_type"] == 5 or order_info["order_type"] == 3:
            if current_price <= order_info["tp"]:
                print(f"Order {order_id} is SELL and reached TP before started")
                remove_all_orders_per_pair(symbol)
                return False
            else:
                print(f"Order {order_id} is sell and ok")
    return True


# Function to monitor and handle order activation
def monitor_orders():
    global orders_dict
    global reached_tp_already
    for pairs_pending in list(orders_dict["pending_orders"].keys()):
        print(pairs_pending)
        for order_id in list(orders_dict["pending_orders"][pairs_pending].keys()):
            if pairs_pending in list(orders_dict["pending_orders"].keys()):
                if (len(orders_dict["pending_orders"][pairs_pending]) == 2):
                    print("Order still not going anywhere")
                    print(f"Lets check if the pair reached its limits {pairs_pending}")
                    reached_tp_already = check_tp(pairs_pending)
                    print(reached_tp_already)
                if reached_tp_already:
                    print(f"Order {order_id} is still in pending orders")
                    if order_id in list(orders_dict["pending_orders"][pairs_pending].keys()):
                        order_info = orders_dict["pending_orders"][pairs_pending][order_id]
                        print(f"Monitoring order {order_id}: {order_info}")
                        orders = mt5.orders_get(ticket=order_id)
                        trades = mt5.positions_get(ticket=order_id)
                        # order = trades[0]  # Gettet the first order from the list
                        symbol = order_info["symbol"]
                        if orders_dict["pending_orders"][symbol][order_id]["tripled"] == False:
                            if trades is not () and orders_dict["pending_orders"][symbol]:
                                print(orders_dict["pending_orders"][symbol][order_id]["tripled"])
                                if orders_dict["pending_orders"][symbol][order_id]["tripled"] == False:
                                    print("3")
                                    print(f"Order {order_id} has been activated as a market order")
                                    orders_dict["active_orders"][symbol][order_id] = order_info  # Move to active orders
                                    print(f"Removing {order_id} for pending orders")
                                    del orders_dict["pending_orders"][symbol][order_id]
                                    # Delete the opposite pending order if it exists
                                    opposite_order_id = get_opposite_order(order_info["symbol"], order_info["order_type"])
                                    print(opposite_order_id)
                                    if opposite_order_id:
                                        print(f"Deleting opposite order {opposite_order_id} for {order_info['symbol']}")
                                        delete_order(opposite_order_id)
                                        print(f"Removed opposite order {opposite_order_id} from pending orders.")
                                    else:
                                        print(f"No opposite order found for {order_info['symbol']}")
                                    print(orders_dict["pending_orders"][order_info["symbol"]][opposite_order_id]["tripled"])
                                    # Place a new pending order in the opposite direction with 3x the lot size (if not already done)
                                    if not orders_dict["pending_orders"][order_info["symbol"]][opposite_order_id]["tripled"]:
                                        order_details = orders_dict["pending_orders"][order_info["symbol"]][opposite_order_id]

                                        # Removing the opposite order from the dictionary, new one will be added
                                        del(orders_dict["pending_orders"][order_details["symbol"]][opposite_order_id])
                                        new_lot = order_details["lot"] * 3
                                        send_order(order_details["symbol"], order_details["order_type"], order_details["price"], order_details["sl"], order_details["tp"], new_lot, order_details["magic"])

                                        # Update the tripled flag to indicate that this order has been placed
                                        for order in orders_dict["pending_orders"][order_details["symbol"]].keys():
                                            orders_dict["pending_orders"][order_details["symbol"]][order]["tripled"] = True
                                            print(f"Updated order {order} to tripled: {orders_dict['pending_orders'][order_details['symbol']][order]}")
                                else:
                                    print(f"Order {order_id} is already tripled.")
                                    print(f"Running state 2 for {symbol}")
                                    stage2(symbol)
                        else:
                            print(f"Order {order_id} is already tripled.")
                            print(f"Running state 2 for {symbol}")
                            stage2(symbol)
                    else:
                        print(f"Order {order_id} is still pending.")
                else:
                    print(f"Order {order_id} should not be in pending orders, this is the last time you will see this pair running")
            else:
                print(f"Order {order_id} should not be in pending orders, this is the last time you will see this pair running")
    return "Stage1"



def stage2(symbol):
    print(f"I Know you have active trade, watching {symbol} for changes.")
    if symbol in list(orders_dict["active_orders"].keys()):
        order_id = list(orders_dict["active_orders"][symbol].keys())
        print(order_id)
        trades = mt5.positions_get(ticket=order_id[0])
        print(trades)
        if trades:
            print(f"Found active order {order_id} for {symbol}")
        else:
            del orders_dict["active_orders"][symbol][order_id[0]]
            print(f"No active order found for {symbol}")
            print(f"Checking if there are pending orders for {symbol}")
            pending_order_id = list(orders_dict["pending_orders"][symbol].keys())
            trades = mt5.positions_get(ticket=pending_order_id[0])
            orders = mt5.orders_get(ticket=pending_order_id[0])
            if trades:
                print(f"Pending order found for {symbol} {pending_order_id} got activated")
                print(f"updating dictionaries")
                orders_dict["active_orders"][symbol][pending_order_id[0]] = orders_dict["pending_orders"][symbol][pending_order_id[0]]
                delete_order(pending_order_id[0])
                del orders_dict["pending_orders"][symbol]
            if orders:
                print(f"Pending order found for {symbol}")
                print(f"Assuming TP reached, updating dictionaries")
                print(f"Anyway finished working for pair")
                delete_order(pending_order_id[0])
                del orders_dict["pending_orders"][symbol]
                del orders_dict["active_orders"][symbol]



# Function to get the opposite order type
def get_opposite_order_type(order_type):
    if order_type == mt5.ORDER_TYPE_BUY_STOP or order_type == mt5.ORDER_TYPE_BUY_LIMIT:
        return mt5.ORDER_TYPE_SELL_STOP
    elif order_type == mt5.ORDER_TYPE_SELL_STOP or order_type == mt5.ORDER_TYPE_SELL_LIMIT:
        return mt5.ORDER_TYPE_BUY_STOP

# Function to find the opposite pending order
def get_opposite_order(symbol, current_order_type):
    print(orders_dict["pending_orders"][symbol])
    for order_id, order_info in orders_dict["pending_orders"][symbol].items():
        if order_info["symbol"] == symbol and order_info["order_type"] != current_order_type:
            print(f"Found opposite order {order_id} for {symbol}")
            return order_id
    return None

# Example of how the EA runs
def process_trade_pairs(pairs):
    for pair in pairs:
        symbol = pair["symbol"]
        buy_price = pair["buy_price"]
        sell_price = pair["sell_price"]
        buy_tp = pair["buy_tp"]
        sell_tp = pair["sell_tp"]
        magic = pair["magic"]

        # Get current price
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            print(f"Failed to get price for {symbol}")
            continue

        current_price = symbol_info.bid
        print(f"Current price for {symbol}: {current_price}")
        lot_size = 0.1  # Set initial lot size
        if testing:
            if symbol == "XAUUSD+":
                buy_price = symbol_info.bid + 1
                buy_tp = symbol_info.bid + 2
                sell_price = symbol_info.bid - 1
                sell_tp = symbol_info.bid - 2
            elif symbol == "DJ30" or symbol == "NAS100" or symbol == "SP500" or symbol == "UK100":
                buy_price = symbol_info.bid + 10
                buy_tp = symbol_info.bid + 20
                sell_price = symbol_info.bid - 10
                sell_tp = symbol_info.bid - 20
            else:
                buy_price = symbol_info.bid + 0.0002
                buy_tp = symbol_info.bid + 0.0004
                sell_price = symbol_info.bid - 0.0002
                sell_tp = symbol_info.bid - 0.0004
        # Place the appropriate pending orders
        if current_price < buy_price:
            print(f"Placing BUY STOP order for {symbol} at {buy_price}")
            order_buy_pending_id = send_order(symbol, mt5.ORDER_TYPE_BUY_STOP, buy_price, sell_price, buy_tp, lot_size, magic)
        else:
            print(f"Placing BUY LIMIT order for {symbol} at {buy_price}")
            order_buy_pending_id = send_order(symbol, mt5.ORDER_TYPE_BUY_LIMIT, buy_price, sell_price, buy_tp, lot_size, magic)

        if current_price > sell_price:
            print(f"Placing SELL STOP order for {symbol} at {sell_price}")
            order_sell_pending_id = send_order(symbol, mt5.ORDER_TYPE_SELL_STOP, sell_price, buy_price, sell_tp, lot_size, magic)
        else:
            print(f"Placing SELL LIMIT order for {symbol} at {sell_price}")
            order_sell_pending_id = send_order(symbol, mt5.ORDER_TYPE_SELL_LIMIT, sell_price, buy_price, sell_tp, lot_size, magic)

# Example data (as per your JSON structure)
pairs = [
    {"symbol": "XAUUSD+", "buy_price": 2655.13, "sell_price": 2651.59, "buy_tp": 2659.22, "sell_tp": 2647.41, "magic": 12345},
    {"symbol": "GBPUSD+", "buy_price": 1.31280, "sell_price": 1.31083, "buy_tp": 1.31504, "sell_tp": 1.30885, "magic": 12345},
    {"symbol": "AUDJPY+", "buy_price": 101.097, "sell_price": 100.888, "buy_tp": 101.335, "sell_tp": 100.668, "magic": 12345},
    {"symbol": "EURUSD+", "buy_price": 1.09798, "sell_price": 1.09683, "buy_tp": 1.09961, "sell_tp": 1.09534, "magic": 12345},
    {"symbol": "EURJPY+", "buy_price": 163.337, "sell_price": 163.021, "buy_tp": 163.589, "sell_tp": 162.717, "magic": 12345},
    {"symbol": "GBPAUD+", "buy_price": 1.93117, "sell_price": 1.92968, "buy_tp": 1.93271, "sell_tp": 1.92820, "magic": 12345},
    {"symbol": "EURAUD+", "buy_price": 1.61587, "sell_price": 1.61439, "buy_tp": 1.61769, "sell_tp": 1.61256, "magic": 12345},
    {"symbol": "DJ30", "buy_price": 42323.90, "sell_price": 42290.56, "buy_tp": 42361.29, "sell_tp": 42249.14, "magic": 12345},
    {"symbol": "NAS100", "buy_price": 20022.71, "sell_price": 19986.37, "buy_tp": 20060.04, "sell_tp": 19950.02, "magic": 12345},
    {"symbol": "SP500", "buy_price": 5749.76, "sell_price": 5742.14, "buy_tp": 5757.93, "sell_tp": 5733.80, "magic": 12345},
    {"symbol": "UK100", "buy_price": 8316.98, "sell_price": 8310.28, "buy_tp": 8324.41, "sell_tp": 8302.57, "magic": 12345}
]


# Initialize MetaTrader 5 connection
mt5.initialize()
for pair in pairs:
    orders_dict["pending_orders"][pair["symbol"]] = {}
    orders_dict["active_orders"][pair["symbol"]] = {}

def count_total_pending_orders():
    pending_orders = 0
    for pair in pairs:
        if pair["symbol"] in orders_dict["pending_orders"]:
            pending_orders += len(orders_dict["pending_orders"][pair["symbol"]])
            trades = mt5.positions_get(symbol=pair["symbol"])
            print(trades)
            pending_orders += len(trades)
    print(f"Total orders: {pending_orders}")
    return pending_orders
# Place pending orders on startup

print("Starting up")
process_trade_pairs(pairs)
# Monitor the orders to handle activation and modifications
pending_orders = count_total_pending_orders()
while pending_orders > 0:
    monitor_orders()
    print(orders_dict)
    time.sleep(2)  # Check every 10 seconds for order activation
    pending_orders = count_total_pending_orders()

# Shutdown the connection after orders are managed
print("Im Done!!!!")
mt5.shutdown()
