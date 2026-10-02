import argparse
import os
from pathlib import Path
import tempfile

def main():
    parser=argparse.ArgumentParser(description='desk helper ui: local demo by default')
    parser.add_argument('--data-dir',type=Path,help='Explicit workspace directory; never reuses another app data folder')
    parser.add_argument('--temporary',action='store_true',help='Disposable demo workspace removed on exit')
    parser.add_argument('--backend',type=Path,help='Explicit trusted Python plugin; arbitrary code, never auto-loaded')
    args=parser.parse_args()
    if args.temporary and args.data_dir:parser.error('--temporary and --data-dir are mutually exclusive')
    from .backends import load_backend
    try:
        backend=load_backend(args.backend) if args.backend else None
    except ValueError:
        parser.error('backend_initialization_failed; review the trusted plugin locally')
    from .app import App
    import tkinter as tk
    default=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'desk-helper-ui'
    if args.temporary:
        with tempfile.TemporaryDirectory(prefix='desk-helper-demo-') as directory:
            root=tk.Tk();App(root,directory,backend);root.mainloop()
    else:
        root=tk.Tk();App(root,args.data_dir or default,backend);root.mainloop()

if __name__=='__main__':main()
