import sys
import multiprocessing

if __name__ == '__main__':
    # Essential for Windows executables using multiprocessing/subprocessing
    multiprocessing.freeze_support()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--run-backend":
        # Launch the autonomous backend
        sys.argv.pop(1)
        import main
        main.main()
    else:
        # Launch the GUI
        import ui
        ui.main()
