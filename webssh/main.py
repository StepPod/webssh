import logging
import tornado.web
import tornado.ioloop

from tornado.options import options
from webssh import handler
from webssh.handler import IndexHandler, WsockHandler, NotFoundHandler
from webssh.settings import (
    get_app_settings,  get_host_keys_settings, get_policy_setting,
    get_ssl_context, get_server_settings, check_encoding_setting
)

# ===== 커스텀 설정: 고정 대상 SSH 프록시 =====
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 2222

# TODO: password, username 등은 cookie를 사용해서 전송할 수 있도록 보안 향상 필요
class FixedIndexHandler(IndexHandler):
    def get_hostname(self):
        return PROXY_HOST
    
    def get_port(self):
        return PROXY_PORT


def make_handlers(loop, options):
    host_keys_settings = get_host_keys_settings(options)
    policy = get_policy_setting(options, host_keys_settings)

    handlers = [
        # 기본 루트는 커스텀 인덱스로 교체
        (r'/', FixedIndexHandler, dict(loop=loop, policy=policy,
                                       host_keys_settings=host_keys_settings)),
        # 웹소켓도 커스텀으로 교체
        (r'/ws', WsockHandler, dict(loop=loop))
    ]
    return handlers

def make_app(handlers, settings):
    settings.update(default_handler_class=NotFoundHandler)
    return tornado.web.Application(handlers, **settings)

def app_listen(app, port, address, server_settings):
    app.listen(port, address, **server_settings)
    if not server_settings.get('ssl_options'):
        server_type = 'http'
    else:
        server_type = 'https'
        handler.redirecting = True if options.redirect else False
    logging.info('Listening on {}:{} ({})'.format(address, port, server_type))

def main():
    options.parse_command_line()
    check_encoding_setting(options.encoding)
    loop = tornado.ioloop.IOLoop.current()
    app = make_app(make_handlers(loop, options), get_app_settings(options))
    ssl_ctx = get_ssl_context(options)
    server_settings = get_server_settings(options)

    app_listen(app, options.port, options.address, server_settings)

    if ssl_ctx:
        server_settings.update(ssl_options=ssl_ctx)
        app_listen(app, options.sslport, options.ssladdress, server_settings)

    loop.start()

if __name__ == '__main__':
    main()
