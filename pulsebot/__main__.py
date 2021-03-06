# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from config import Config
from irc import Bot
from treestatus import (
    TreeStatus,
    UnknownBranch,
)
from pulse_dispatch import PulseDispatcher
import os


config = Config('pulsebot.cfg')

treestatus = TreeStatus(config.treestatus.server)

bot = Bot(config)

dispatcher = PulseDispatcher(bot.msg, config)

for command, where, nick in bot:
    verb, args = command[0], command[1:]
    if verb == 'status':
        if len(args) != 1:
            bot.msg(where, nick, 'Try again with "status <branch>"')
        else:
            branch = args[0]
            try:
                status = treestatus.current_status(branch)
                bot.msg(
                    where, nick,
                    '%s is %s' % (status['tree'], status['status'].upper())
                )
            except UnknownBranch:
                bot.msg(where, nick, 'Unknown branch: %s' % branch)
    elif verb == 'retry':
        # This isn't very secure, but then the action is presumably not very
        # sensitive.
        if where == nick == bot.owner:
            url = args[0]
            for push in dispatcher.hgpushes.get_push_info_from(url):
                dispatcher.report_one_push(push)
    elif verb == 'reload':
        if where == nick == bot.owner:
            new_config = Config('pulsebot.cfg')
            use_new = False
            if new_config.treestatus.server != config.treestatus.server:
                treestatus = TreeStatus(new_config.treestatus.server)
                use_new = True

            if (any(getattr(new_config, k) != getattr(config, k)
                    for k in ('dispatch', 'bugzilla_branches',
                              'bugzilla_leave_open'))):
                dispatcher.config = new_config
                use_new = True

            if new_config.core.channels != config.core.channels:
                channels = set(config.core.channels)
                new_channels = set(new_config.core.channels)
                for c in new_channels - channels:
                    bot.join(c)
                for c in channels - new_channels:
                    bot.part(c)

            if use_new:
                config = new_config


dispatcher.shutdown()
bot.shutdown()
# Sopel doesn't terminate all its threads, so kill them all
os._exit(0)
