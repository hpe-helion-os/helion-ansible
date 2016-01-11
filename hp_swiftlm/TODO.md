1. Too much mocking in tests, many of which arent used or are just repetative.
2. Tests used seperate data files. If they really require them they should
   exist as constants in each test file.
3. Invalid Constant names in the core code.
4. Inconsistent return values from each checks `main()`.
5. Seems to be no logging in core code.
6. Seperate Constant files in core code. These should be places into config
   files rather than the code itself.
7. Utility commands spread across multiple files and and many in class
   methods when functions would suit better.
8. Utility functions shelling out for text processing using `grep`, `awk`, and
   `sed`
9. Unneeded Message class in some check files.
10. Checks should return python structures. The `if __name__ == '__main__':`
  block can format them for printing if called as a single script.

## Nits
11. Backslash continuation rather than brackets.
12. Old style text formating, `%s` instead of `{}`
13. Using old style Octal formatting `0777` instead of `0o777`
14. Using ast.literal_eval, Hopefully this can be removed.
15. Add Util function for Popen if we are going to be usign it so much. 99% of
    the time we want PIPE stdout+stdin
