#!/usr/bin/env python
''' Make sure to run with sudo -E to be superuser while maintaing standard user environment variables'''
import time
import slackbots as sb
import argparse
import scapy.all as sc
import pdb

WEBHOOK="https://hooks.slack.com/services/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"
SECURITY_ROOM="security"

def NetworkChanges(current, prior):
    added_macs = set(current) - set(prior)
    dropped_macs = set(prior) - set(current)
    res = {'added': added_macs, 'dropped': dropped_macs}
    return res

def ARPScan(ip_range):
    ans,unans=sc.srp(sc.Ether(dst="ff:ff:ff:ff:ff:ff")/sc.ARP(pdst=ip_range),timeout=10)
    return ans

def ParseArgs():
    parser = argparse.ArgumentParser(description='ARP scan a network on a schedule.')
    parser.add_argument('network_ip', type=str, help='the network addresses to scan')
    parser.add_argument('-s', '--scan', type=int, dest='scan_frequency', default=300, help='frequency to scan the network (in seconds)')
    return parser

def TalkToMeGoose(bot, mac_changes):
    added_macs = ""
    dropped_macs = ""
    if len(mac_changes['added']):
        added_macs = "added macs:\n" + "\n".join(mac_changes['added'])
    if len(mac_changes['dropped']):
        dropped_macs = "dropped macs:\n" + "\n".join(mac_changes['dropped'])
    message = added_macs + dropped_macs
    print '[!!] message: %s' % message
    bot.say_something(message, bot.channel_id)

if __name__ == "__main__":
    parser = ParseArgs()
    args = parser.parse_args()
    print '[!!] args: %s' % args
    bot = sb.SlackBot(SECURITY_ROOM)
    print '[!!] channel id: %s' % bot.channel_id
    prior_devices, current_devices = {}, {}
    while True:
        print "[!!] %s Running.." % time.ctime(time.time())
        ans=ARPScan(args.network_ip)
        current_devices = dict([(r[1].hwsrc, r[1].psrc) for r in ans])
        diff = NetworkChanges(current_devices, prior_devices)
        TalkToMeGoose(bot, diff)
        print '[!!] diff: %s' % diff
        print ans.summary()
        prior_devices = current_devices
        time.sleep(args.scan_frequency)
        #check ans against last run, send message to slack room on diffs
