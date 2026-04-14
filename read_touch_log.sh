#!/bin/bash
# Quick script to read the touch debug log
cat touch_debug.log 2>/dev/null || echo "Log file not found yet. Run the GUI first and touch the buttons."
