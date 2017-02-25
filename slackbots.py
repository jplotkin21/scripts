#!/usr/bin/env python

import os
from slackclient import SlackClient
import MySQLdb
import re
import datetime as dt
import pdb
from pytz import timezone

#timezone
LOCAL_TZ = timezone(os.environ.get("LOCAL_TIMEZONE", None))
UTC_TZ = timezone("UTC")
DATETIME_FMT = "%d%b%y %I:%M%p"
#slack configs
SLACK_TOKEN = os.environ.get("SLACK_TOKEN", None)

#default bot configs
DEFAULT_USERNAME = "BOT"
DEFAULT_BOT_EMOJI = ":robot_face:"

#grocery bot configs
GROCERY_ROOM = 'general'
GROCERY_USERNAME = 'mrpear'
GROCERY_BOT_EMOJI = ':pear:'
#grocery bot configs to connect to db
GROCERY_DB_HOST='localhost'
GROCERY_DB_USER='master'
GROCERY_DB_PASS='password'
GROCERY_DB_NAME='groceries'
GROCERY_TABLE='shoppinglist'

def update_func(message):
    quantity = re.match(r"(\d)\s", message) 
    if quantity is not None:
        quantity = int(quantity.groups()[0])
        item = re.match(r"[0-9]\s(.*)", message)
        item = item.groups()[0]
        #what an utter hack job
        item = item.split(" to the list")[0]
    else:
        quantity = 1
        item = message
    res = {
        'message': "add %d %s" % (quantity, item),
        'quantity': quantity,
        'item': item
        }
    return res
 
def update_resp_func(context):
    resp_body = "Hey %s, so you want me to add %d %s to the list, right?"
    resp = resp_body % (context['username'], context['quantity'], context['item'])
    return resp

def remove_func(message):
    quantity = re.match(r"(\d)\s", message)
    if quantity is not None:
        quantity = int(quantity.groups()[0])
        item = re.match(r"[0-9]\s(.*)", message)
        item = item.groups()[0]
    else:
        quantity = ""
        item = message
    res = {
        'message': "remove %s %s" % (str(quantity), item),
        'quantity': quantity,
        'item': item
        }
    return res

def remove_resp_func(context):
    resp_body = "Hey %s, you want %s %s removed, yeah?"
    resp = resp_body % (context['username'], context['quantity'], context['item'])
    return resp

def clean_func(message):
    res = {
            'message': "remove %s" % message,
        'item': message
        }
    return res

def clean_resp_func(context):
    resp_body = "Yo %s, you bought %s eh?"
    resp = resp_body % (context['username'], context['item'])
    return resp

def show_func(message):
    return {'message': 'showing the current list!'}

#BotResponse configs...should this be a json in another file?
GROCERY_RESPONSE_CONFIG = {
            "update": 
            {
                "re": r".*(?<=(?<=add)|(?<=insert))\s(.*)",
                "func": update_func, 
                "response_function": update_resp_func
            },
            "show":
            {
                "re": r"^(?=.*list)(?=.*show)",
                "func": show_func,
                "response_function": None
            },
            "remove":
            {
                "re": r".*(?<=(?<=remove)|(?<=drop))\s(.*)",
                "func": remove_func,
                "response_function": remove_resp_func
            },
            "clean":
            {
                "re": r".*(?<=(?<=clean)|(?<=close)|(?<=purchased)|(?<=bought))\s(.*)",
                "func": clean_func,
                "response_function": clean_resp_func
            }
        }

def db_query(sql):
    print '[!!] attempting to connect to db...'
    db = MySQLdb.connect(host=GROCERY_DB_HOST,
            user=GROCERY_DB_USER,
            passwd=GROCERY_DB_PASS,
            db=GROCERY_DB_NAME
            )
    cr = db.cursor()
    print '[!!] connection successful!'
    print '[!!] runnning query %s' % sql
    cr.execute(sql) 
    if "SELECT" in sql.upper():
        res = cr.fetchall()
    else:
        res = 1
        db.commit()
    cr.close()
    db.close()
    return res

class BotResponses(object):
    """Encapsulates logic for responding to slack messages from users. Config is a dict of names: re pairs"""    
    def __init__(self, config):
        self.config = config

    def process_command(self, message):
        """This is for the initial command sent by the user. We will then pass back to confirm with a context.
        The confirm response will be handled by the process_response method
        """ 
        print '[!!] message about to be processed: %s' % message
        res, context = {}, {}
        context['msg_time'] = dt.datetime.now()
        for k, v in self.config.iteritems():
            re_match = re.match(v["re"], message) 
            if re_match is not None:
                re_match = re_match.groups()
                re_match = re_match[0] if len(re_match) > 0 else '' 
                print '[!!] match: %s: %s' % (k, re_match)
                res[k] = re_match
        print '[!!] res = %s' % res
        if len(res) == 0:
            response = "Sorry, I didn't catch that, can you try again?"
            context['method'] = 'Unknown'
        elif len(res) == 1:
            config_vals = self.config[res.keys()[0]]           
            context.update(config_vals['func'](res.values()[0]))
            context['method'] = res.keys()[0]
            context['response_function'] = config_vals['response_function']
            response = context.pop("message")
        else:
            response = "A bit confused here, did you want to %s?" % " or ".join(res.keys())
            context["response_categories"] = res.keys()
            context["message"] = message
        return (response, context)

class SlackBot(object):
    def __init__(self, channel_name=None):
        self.sc = SlackClient(SLACK_TOKEN)
        self.conversation_context = None
        self.channel_name=channel_name
        channel_list = self.list_channels()
        if self.channel_name != None:
            self.channel_id = [v for v in channel_list if v['name'] == self.channel_name][0]['id']
        else:
            self.channel_id = None

    def list_channels(self):
        channels_call = self.sc.api_call("channels.list")
        if channels_call['ok']:
            return channels_call['channels']
        return None
    
    def channel_info(channel_id):
        channel_info = sc.api_call("channels.info", channel=channel_id)
        if channel_info:
            return channel_info['channel']
        return None

    def say_something(self, message, channel_id, user=DEFAULT_USERNAME, emoji=DEFAULT_BOT_EMOJI):
        self.sc.api_call("chat.postMessage",
                channel=channel_id,
                text=message,
                username=user,
                icon_emoji=emoji
                )

class GroceryBot(SlackBot):
    def __init__(self):
        super(GroceryBot, self).__init__()
        channel_list = self.list_channels()
        self.channel_name = GROCERY_ROOM
        self.channel_id = [v for v in channel_list if v['name'] == self.channel_name][0]['id']
        self.resp = BotResponses(GROCERY_RESPONSE_CONFIG)

    def say_something(self, message):
        super(GroceryBot, self).say_something(message, self.channel_id, GROCERY_USERNAME, GROCERY_BOT_EMOJI)

    def offer_help(self):
        """print how to best interact with mrpear"""
        help_message = "you can say things like 'add eggs to the list' or 'show me the list' or 'remove eggs from the list'"
        self.say_something(help_message)

    def show(self, context = None):
        res = db_query("select * from %s where closed_by is null;" % GROCERY_TABLE)
        res_string = ""
        for r in res:
            utc_time = r[2].replace(tzinfo=UTC_TZ)
            local_time = utc_time.astimezone(LOCAL_TZ)
            formatted_time = local_time.strftime(DATETIME_FMT)
            res_string += "%d %s added by %s on %s\n" % (r[1], r[0], r[4], formatted_time)
        return res_string
        
    def update(self, context):
        #TODO need some error handling here (and in remove, show)
        sql = "INSERT INTO %s (gitem, g_quantity, added_by) VALUES ('%s', %d, '%s');" % \
            (GROCERY_TABLE, context['item'], context['quantity'], str(context['username']))
        print sql
        db_query(sql)

    def clean(self, context):
        sql = "UPDATE %s SET purchase_date='%s', closed_by='%s' WHERE gitem='%s' and closed_by is NULL;" % \
            (GROCERY_TABLE,context['msg_time'],context['username'],context['item'])
        db_query(sql)

    def remove(self, context):
        recs = db_query("select * from %s where closed_by is null;" % GROCERY_TABLE)
        idx = [i for i, a in enumerate(recs) if context['item'] in a]
        if len(idx) != 0:
            if context['quantity'] != "":
                #we are updating quantity
                sql = "UPDATE %s SET g_quantity='%s' WHERE gitem='%s';" % \
                        (GROCERY_TABLE, context['quantity'], context['item'])
            else:
                #we are removing everything
                sql = "DELETE FROM %s WHERE gitem='%s';" % (GROCERY_TABLE, context['item'])
            db_query(sql)

    def listen(self, message, user = None):
        """to begin just switch on 'add/update', 'show', 'remove'"""
        if self.conversation_context == None:
            resp, self.conversation_context = self.resp.process_command(message)
            print '[!!] message -> %s, response -> %s' % (message, resp)
            print '[!!] context: %s' % self.conversation_context
            self.conversation_context['username'] = user
            if self.conversation_context['method'] == 'Unknown':
                #something went wrong
                self.say_something(resp)
                self.conversation_context = None
            elif self.conversation_context['method'] == 'show':
                #no back and forth, so just show and be done
                func = getattr(self, "show")
                try:
                    grocery_list = func(self.conversation_context)
                    print '[!!] grocery list: %s' % grocery_list
                    self.say_something(grocery_list)
                except:
                    self.say_something("Sorry, I've been drinking more lately...")
                self.conversation_context = None
            else:
                resp_func = self.conversation_context['response_function']
                response = resp_func(self.conversation_context)
                self.say_something(response)
        else:
            #nothing fancy here, if they say yes, process the transaction from the context
            #if they say no, then just tell them your giving up
            yes = re.match(r".*(?<=(?<=y)|(?<=yes))", message)
            no = re.match(r".*(?<=(?<=n)|(?<=no))", message)
            if yes is not None and no is None:
                func = getattr(self, self.conversation_context['method'])
                try:
                    func(self.conversation_context)
                    self.say_something("Done! Horray!")
                except:
                    self.say_something("Oh no something went wrong. I'm a little clumsy, can we try again?")
            elif no is not None and yes is None:
                self.say_something("err, sorry, maybe try again? im still learning")
            else:
                self.say_something("yikes! i got really confused, can we try again?")
            self.conversation_context = None

if __name__ == '__main__':
    gb = GroceryBot()
#    gb.say_something("Hello from MrPear at %s!" % dt.datetime.now())
    print gb.show()
    gb.listen("hey mrpear, remove condoms")
    gb.listen("mrpear, yes")
#    gb.listen("mrpear, show the list please")
#    gb.listen("mrpear, add cookies")
#    gb.listen("mrpear, yes")
#    gb.listen("mrpear, show the list please")
#    gb.listen("mrpear, remove cookies")
#    gb.listen("mrpear, yes")
#    gb.listen("mrpear, show the list")
#    gb.listen("mrpear, i bought yogurt")  
#    gb.listen("mrpear, yes")
#    gb.listen("mrpear, show the list")
