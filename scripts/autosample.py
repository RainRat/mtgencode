#!/usr/bin/env python3
import os
import sys
import subprocess
import random

def extract_cp_name(name):
    # "lm_lstm_epoch50.00_0.1870.t7"
    if not (name[:13] == 'lm_lstm_epoch' and name[-3:] == '.t7'):
        return None
    name = name[13:-3]
    try:
        parts = name.split('_')
        if len(parts) != 2:
            return None
        return (float(parts[0]), float(parts[1]))
    except (ValueError, TypeError):
        return None

def sample(cp, temp, count, seed = None, ident = 'output', dry_run = False):
    if seed is None:
        seed = random.randint(-1000000000, 1000000000)
    outfile = cp + '.' + ident + '.' + str(temp) + '.txt'

    cmd_for_log = ('th sample.lua ' + cp
                   + ' -temperature ' + str(temp)
                   + ' -length ' + str(count)
                   + ' -seed ' + str(seed)
                   + ' >> ' + outfile)

    cmd_for_exec = ['th', 'sample.lua', cp,
                    '-temperature', str(temp),
                    '-length', str(count),
                    '-seed', str(seed)]

    if dry_run:
        return {
            'checkpoint': cp,
            'outfile': outfile,
            'exists': os.path.exists(outfile),
            'cmd': cmd_for_log,
            'exec_cmd': cmd_for_exec
        }

    if os.path.exists(outfile):
        print(f"{outfile} already exists, skipping")
        return False
    else:
        with open(outfile, 'w') as f:
            f.write(cmd_for_log + '\n')

        with open(outfile, 'a') as f:
            subprocess.run(cmd_for_exec, stdout=f)
        return True

def find_best_cp(cpdir):
    best = None
    best_cp = None
    for path in os.listdir(cpdir):
        fullpath = os.path.join(cpdir, path)
        if os.path.isfile(fullpath):
            extracted = extract_cp_name(path)
            if extracted is not None:
                (epoch, vloss) = extracted
                if best is None or vloss < best:
                    best = vloss
                    best_cp = fullpath
    return best_cp

def process_dir(cpdir, temp, count, seed = None, ident = 'output', verbose = False, dry_run = False, _top = True, _results = None):
    if _results is None:
        _results = {'dirs': 0, 'samples': []}
    _results['dirs'] += 1

    if verbose:
        print(('processing ' + cpdir))
    best_cp = find_best_cp(cpdir)
    if best_cp is not None:
        sample_res = sample(best_cp, temp, count, seed=seed, ident=ident, dry_run=dry_run)
        if dry_run and sample_res:
            _results['samples'].append(sample_res)

    for path in sorted(os.listdir(cpdir)):
        fullpath = os.path.join(cpdir, path)
        if os.path.isdir(fullpath):
            process_dir(fullpath, temp, count, seed=seed, ident=ident, verbose=verbose, dry_run=dry_run, _top=False, _results=_results)

    if dry_run and _top:
        scanned_dirs = _results['dirs']
        samples = _results['samples']
        total_cps = len(samples)
        existing_count = sum(1 for s in samples if s['exists'])
        new_count = total_cps - existing_count

        print("Dry Run Summary:")
        print(f"  Directories scanned: {scanned_dirs}")
        print(f"  Checkpoints identified: {total_cps}")
        print(f"  Target output files: {total_cps} ({new_count} new, {existing_count} already existing)")
        if samples:
            print("Sample Commands Preview (up to 10):")
            for item in samples[:10]:
                status = "[EXISTS]" if item['exists'] else "[NEW]"
                print(f"  {status} {item['cmd']}")
        return _results

    return _results['samples'] if dry_run else None

def main(rnndir, cpdir, temp, count, seed = None, ident = 'output', verbose = False, dry_run = False):
    if not os.path.isdir(rnndir):
        raise ValueError('bad rnndir: ' + rnndir)
    if not os.path.isdir(cpdir):
        raise ValueError('bad cpdir: ' + cpdir)
    if not dry_run:
        os.chdir(rnndir)
    return process_dir(cpdir, temp, count, seed=seed, ident=ident, verbose=verbose, dry_run=dry_run)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        prog='autosample.py',
        description='Automatically sample text from trained Torch model checkpoints across nested directories.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Usage Examples:
  # Process all checkpoint subdirectories in a model folder
  python3 scripts/autosample.py /path/to/rnn_repo /path/to/checkpoints

  # Preview sampling commands and identified checkpoints without executing (dry-run)
  python3 scripts/autosample.py /path/to/rnn_repo /path/to/checkpoints --dry-run

  # Specify custom sampling temperature and character count
  python3 scripts/autosample.py /path/to/rnn_repo /path/to/checkpoints -t 0.8 -c 500000
'''
    )

    parser.add_argument('rnndir',
                        help='base rnn directory, must contain sample.lua')
    parser.add_argument('cpdir',
                        help='checkpoint directory, all subdirectories will be processed')
    parser.add_argument('-t', '--temperature', action='store', default='1.0',
                        help='sampling temperature')
    parser.add_argument('-c', '--count', action='store', default='1000000',
                        help='number of characters to sample each time')
    parser.add_argument('-s', '--seed', action='store', default=None,
                        help='fixed seed; if not present, a random seed will be used')
    parser.add_argument('-i', '--ident', action='store', default='output',
                        help='identifier to include in the output filenames')
    parser.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a dry run summary preview of identified checkpoints and sampling commands without running sample.lua or writing output files.')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='verbose output')

    args = parser.parse_args()
    if args.seed is None:
        seed = None
    else:
        seed = int(args.seed)
    main(args.rnndir, args.cpdir, float(args.temperature), int(args.count), 
         seed=seed, ident=args.ident, verbose=args.verbose, dry_run=args.dry_run)
    sys.exit(0)
