#!/usr/bin/env python3
import os
import shutil

def cleanup_dump(dumpstr):
    cardfrags = dumpstr.split('\n\n')
    if len(cardfrags) < 4:
        return ''
    else:
        return '\n\n'.join(cardfrags[2:-1]) + '\n\n'

def identify_checkpoints(basedir, ident):
    cp_infos = []
    for path in os.listdir(basedir):
        fullpath = os.path.join(basedir, path)
        if not os.path.isfile(fullpath):
            continue
        if not (path[:13] == 'lm_lstm_epoch' and path[-4:] == '.txt'):
            continue
        if ident not in path:
            continue
        # attempt super hacky parsing
        inner = path[13:-4]
        halves = inner.split('_')
        if not len(halves) == 2:
            continue
        parts = halves[1].split('.')
        if not len(parts) == 6:
            continue
        # lm_lstm_epoch[25.00_0.3859.t7.output.1.0].txt
        if not parts[3] == ident:
            continue
        epoch = halves[0]
        vloss = '.'.join([parts[0], parts[1]])
        temp = '.'.join([parts[4], parts[5]])
        cpname = 'lm_lstm_epoch' + epoch + '_' + vloss + '.t7'
        cp_infos += [(fullpath, os.path.join(basedir, cpname),
                      (epoch, vloss, temp))]
    return cp_infos

def _scan_checkpoints(basedir, targetdir, ident, copy_cp):
    (basepath, basedirname) = os.path.split(basedir)
    if basedirname == '':
        (basepath, basedirname) = os.path.split(basepath)

    effective_targetdir = targetdir if targetdir is not None else '[dry-run]'
    records = []
    cmd_files = []

    cp_infos = identify_checkpoints(basedir, ident)
    for (dpath, cpath, (epoch, vloss, temp)) in cp_infos:
        dname = basedirname + '_epoch' + epoch + '_' + \
            vloss + '.' + ident + '.' + temp + '.txt'
        cname = basedirname + '_epoch' + epoch + '_' + vloss + '.t7'
        tdpath = os.path.join(effective_targetdir, dname)
        tcpath = os.path.join(effective_targetdir, cname)
        has_cp = os.path.isfile(cpath)
        records.append({
            'dpath': dpath,
            'dname': dname,
            'tdpath': tdpath,
            'cpath': cpath,
            'cname': cname,
            'tcpath': tcpath,
            'has_cp': has_cp,
            'epoch': epoch,
            'vloss': vloss,
            'temp': temp
        })

    if copy_cp and len(cp_infos) > 0:
        cmdpath = os.path.join(basedir, 'command.txt')
        tcmdpath = os.path.join(effective_targetdir, basedirname + '.command')
        if os.path.isfile(cmdpath):
            cmd_files.append((cmdpath, tcmdpath))

    for path in os.listdir(basedir):
        fullpath = os.path.join(basedir, path)
        if os.path.isdir(fullpath):
            sub_records, sub_cmds = _scan_checkpoints(fullpath, targetdir, ident, copy_cp)
            records.extend(sub_records)
            cmd_files.extend(sub_cmds)

    return records, cmd_files

def process_dir(basedir, targetdir=None, ident = 'output', copy_cp = False, verbose = False, dry_run = False):
    if dry_run:
        effective_targetdir = targetdir if targetdir is not None else '[dry-run]'
        records, cmd_files = _scan_checkpoints(basedir, targetdir, ident, copy_cp)

        if verbose:
            for r in records:
                print('found dumpfile ' + r['dpath'])
                print('    cpx ' + r['dpath'] + ' ' + r['tdpath'])
                if copy_cp and r['has_cp']:
                    print('    cp ' + r['cpath'] + ' ' + r['tcpath'])
            for cpath, tcmdpath in cmd_files:
                print('    cp ' + cpath + ' ' + tcmdpath)

        cp_available_count = sum(1 for r in records if r['has_cp'])
        print(f"Dry Run Summary: {len(records)} checkpoint dump file(s) identified.")
        print(f"  Base Directory: {basedir}")
        print(f"  Target Directory: {effective_targetdir}")
        print(f"  Checkpoints (.t7) Available: {cp_available_count} (Copy Checkpoints: {'Yes' if copy_cp else 'No'})")
        if copy_cp:
            print(f"  Command Files Identified: {len(cmd_files)}")

        if records:
            print("Sample Identified Checkpoints (up to 10):")
            for r in records[:10]:
                print(f"  - epoch {r['epoch']}, vloss {r['vloss']}, temp {r['temp']}: {r['dpath']} -> {r['dname']}")

        print("Dry run complete. No files were written or copied.")
        return

    if targetdir is None:
        raise ValueError("targetdir must be specified when dry_run is False")

    (basepath, basedirname) = os.path.split(basedir)
    if basedirname == '':
        (basepath, basedirname) = os.path.split(basepath)

    cp_infos = identify_checkpoints(basedir, ident)
    for (dpath, cpath, (epoch, vloss, temp)) in cp_infos:
        if verbose:
            print(('found dumpfile ' + dpath))
        dname = basedirname + '_epoch' + epoch + '_' + \
            vloss + '.' + ident + '.' + temp + '.txt'
        cname = basedirname + '_epoch' + epoch + '_' + vloss + '.t7'
        tdpath = os.path.join(targetdir, dname)
        tcpath = os.path.join(targetdir, cname)
        if verbose:
            print(('    cpx ' + dpath + ' ' + tdpath))
        with open(dpath, 'rt') as infile:
            with open(tdpath, 'wt') as outfile:
                outfile.write(cleanup_dump(infile.read()))
        if copy_cp:
            if os.path.isfile(cpath):
                if verbose:
                    print(('    cp ' + cpath + ' ' + tcpath))
                shutil.copy(cpath,  tcpath)

    if copy_cp and len(cp_infos) > 0:
        cmdpath = os.path.join(basedir, 'command.txt')
        tcmdpath = os.path.join(targetdir, basedirname + '.command')
        if os.path.isfile(cmdpath):
            if verbose:
                print(('    cp ' + cmdpath + ' ' + tcmdpath))
            shutil.copy(cmdpath,  tcmdpath)

    for path in os.listdir(basedir):
        fullpath = os.path.join(basedir, path)
        if os.path.isdir(fullpath):
            process_dir(fullpath, targetdir, ident, copy_cp=copy_cp, verbose=verbose, dry_run=False)

main = process_dir

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='collect_checkpoints.py',
        description='Collect and organize neural network checkpoint dumps, model files, and training commands into a target directory.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Usage Examples:
  # Collect output dumps from RNN directory to a target folder
  python3 scripts/collect_checkpoints.py basedir targetdir

  # Collect output dumps and copy matching model checkpoint files
  python3 scripts/collect_checkpoints.py basedir targetdir -c

  # Dry-run preview without copying or writing any files
  python3 scripts/collect_checkpoints.py basedir -p
'''
    )

    parser.add_argument('basedir',
                        help='base rnn directory containing checkpoints and sample output files')
    parser.add_argument('targetdir', nargs='?', default=None,
                        help='checkpoint output directory (optional if --dry-run is specified)')
    parser.add_argument('-c', '--copy_cp', action='store_true', 
                        help='copy checkpoints (.t7) and command files used to generate output files')
    parser.add_argument('-i', '--ident', action='store', default='output',
                        help='identifier string to look for in dump filenames (default: output)')
    parser.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='print a summary of identified checkpoints and target paths without copying or writing files')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='verbose output')

    args = parser.parse_args()

    if not args.dry_run and args.targetdir is None:
        parser.error('the following arguments are required: targetdir (unless --dry-run is specified)')

    try:
        main(args.basedir, args.targetdir, ident=args.ident, copy_cp=args.copy_cp, verbose=args.verbose, dry_run=args.dry_run)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
