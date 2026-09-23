#!/usr/bin/env python3

# -- STOLEN FROM torch-rnn/scripts/streamfile.py -- #

import os
import threading
import time
import signal
import traceback
import psutil

# correctly setting up a stream that won't get orphaned and left cluttering the operating
# system proceeds in 3 parts:
#   1) invoke install_suicide_handlers() to ensure correct behavior on interrupt
#   2) get threads by invoking spawn_stream_threads
#   3) invoke wait_and_kill_self_noreturn(threads)
# or, use the handy wrapper that does it for you

def spawn_stream_threads(fds, runthread):
    threads = []
    for i, fd in enumerate(fds):
        stream_thread = threading.Thread(target=runthread, args=(i, fd))
        stream_thread.daemon = True
        stream_thread.start()
        threads.append(stream_thread)
    return threads

def force_kill_self_noreturn():
    # We have a strange issue here, which is that our threads will refuse to die
    # to a normal exit() or sys.exit() because they're all blocked in write() calls
    # on full pipes; the simplest workaround seems to be to ask the OS to terminate us.
    # This kinda works, but...
    #os.kill(os.getpid(), signal.SIGTERM)
    # psutil might have useful features like checking if the pid has been reused before killing it.
    # Also we might have child processes like l2e luajits to think about.
    me = psutil.Process(os.getpid())
    for child in me.children(recursive=True):
        child.terminate()
    me.terminate()

def handler_kill_self(signum, frame):
    if signum != signal.SIGQUIT:
        traceback.print_stack(frame)
        print(
            ('caught signal {:d} - streamer sending SIGTERM to self'.format(signum)))
    force_kill_self_noreturn()

def install_suicide_handlers():
    for sig in [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, handler_kill_self)

def wait_and_kill_self_noreturn(threads):
    running = True
    while running:
        running = False
        for thread in threads:
            if thread.is_alive():
                running = True
        if(os.getppid() <= 1):
            # exit if parent process died (and we were reparented to init)
            break
        time.sleep(1)
    force_kill_self_noreturn()

def streaming_noreturn(fds, write_stream):
    install_suicide_handlers()
    threads = spawn_stream_threads(fds, write_stream)
    wait_and_kill_self_noreturn(threads)
    assert False, 'should not return from streaming'

# -- END STOLEN FROM torch-rnn/scripts/streamfile.py -- #

import sys
import random

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils
import jdecode

def main(args):
    fds = args.fds
    fname = args.fname
    block_size =  args.block_size
    main_seed = args.seed if args.seed != 0 else None

    # simple default encoding for now, will add more options with the curriculum
    # learning feature

    cards = jdecode.mtg_open_file(fname, verbose=True, linetrans=True)

    def write_stream(i, fd):
        if main_seed is not None:
            local_random = random.Random(main_seed + i)
        else:
            local_random = random.Random()
        local_cards = [card for card in cards]
        with open('/proc/self/fd/'+str(fd), 'wt') as f:
            while True:
                local_random.shuffle(local_cards)
                for card in local_cards:
                    f.write(card.encode(randomize_mana=True, randomize_lines=True))
                    f.write(utils.cardsep)

    streaming_noreturn(fds, write_stream)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='streamcards.py',
        description='Stream encoded card data to one or more file descriptors for concurrent IPC or sub-process pipelines.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Stream cards to file descriptor 3
  python3 scripts/streamcards.py 3 -f data/output.txt

  # Stream cards to multiple file descriptors with a fixed random seed
  python3 scripts/streamcards.py 3 4 5 -s 12345
"""
    )

    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('fds', type=int, nargs='*',
                        help='File descriptors (integers) to write streams to.')
    io_group.add_argument('-f', '--fname', default=os.path.join(libdir, '../data/output.txt'),
                        help='Input card dataset file to stream from (default: data/output.txt).')

    settings_group = parser.add_argument_group('Stream Settings')
    settings_group.add_argument('-n', '--block_size', type=int, default=10000,
                        help='Number of characters each stream buffer reads or writes at a time (default: 10000).')
    settings_group.add_argument('-s', '--seed', type=int, default=0,
                        help='Random seed for shuffling cards (default: 0).')

    if len(sys.argv) == 1 and sys.stdin.isatty():
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not args.fds:
        parser.error('the following arguments are required: fds')

    main(args)
