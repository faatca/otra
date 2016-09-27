import argparse
import sys
import pymongo

from . import db, app


def manage():
    parser = argparse.ArgumentParser(
        description='Otra service management tool')
    subparsers = parser.add_subparsers(
        title='command', description='the management command to execute')

    init_parser = subparsers.add_parser(
        'init', help='initializes the database indexes')
    init_parser.add_argument('--clear', action='store_true')
    init_parser.set_defaults(func=do_init)

    serve_parser = subparsers.add_parser(
        'serve', help='starts a development server')
    serve_parser.add_argument('--public', action='store_true')
    serve_parser.add_argument('--port', type=int, default=5006)
    serve_parser.add_argument('--profile', action='store_true')
    serve_parser.set_defaults(func=do_serve)

    args = parser.parse_args()

    if 'func' not in args:
        parser.print_usage(sys.stderr)
        sys.exit(-1)

    args.func(args)


def do_init(args):
    if args.clear:
        db.users.drop()

    db.users.create_index(
        [("ten", pymongo.ASCENDING), ("uid", pymongo.ASCENDING)],
        unique=True)
    db.users.create_index(
        [("ten", pymongo.ASCENDING), ("old_addr", pymongo.ASCENDING)],
        unique=True)


def do_serve(args):
    host = '' if args.public else '127.0.0.1'
    if args.profile:
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.config['PROFILE'] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

    app.run(host=host, port=args.port, debug=True)
