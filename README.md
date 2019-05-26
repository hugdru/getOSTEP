# getOSTEP
Get the Operating Systems: Three Easy Pieces pdf files

`
❯ ./helper run -d "$HOME/books/ostep"
❯ pdftk "$HOME/books/ostep/*.pdf" cat output "Operating Systems: Three Easy Pieces.pdf"
`
`
❯ ./helper -h                                                                                                     !937
helper (run|env [-f])
  run # runs the code
  env [-f] # creates the environment
    -f # forces env recreation and installs the requirements
`
`
❯ python app.py --help                                                                                            !938
usage: app.py [-h] -d DIRECTORY [-u URL] [-e ERRDATA_URL] [-f]
              [-l ERRDATA_FILENAME]

Get all the pdfs from Operating Systems: Three Easy Pieces

optional arguments:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        The output directory
  -u URL, --url URL     The url to OSTEP
  -e ERRDATA_URL, --errdata-url ERRDATA_URL
                        The url to the errdata of OSTEP
  -f, --force           Force the download
  -l ERRDATA_FILENAME, --errdata-filename ERRDATA_FILENAME
                        The errdata filename to check if you already have the
                        latest version
`
