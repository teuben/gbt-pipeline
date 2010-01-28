@compilePipeline.pro

; arguments:
;   0 -- infile
;   1 -- begin-scan
;   2 -- end-scan
;   3 -- vsource-center
;   4 -- vsource-width
;   5 -- vsource-begin
;   6 -- vsource-end
;   7 -- sdfits-dir
;   8 -- refscan1
;   9 -- refscan2
;  10 -- all-scans-as-ref
;  11 -- debug

args = command_line_args()
print,args

infile=args[0]
beginscan=args[1]
endscan=args[2]
; for tosiaps
; set velocity parameters for selecting relevant channels
vSource=float(args[3])
vSourceWidth=float(args[4])
vSourceBegin=float(args[5])
vSourceEnd=float(args[6])
sdfitsdir=args[7]
refscan1=fix(args[8])
refscan2=fix(args[9])
allscansref=fix(args[10])
VERBOSE=fix(args[11])

if (VERBOSE gt 2) then print,args

infileOK    = FILE_TEST(infile)
sdfitsdirOK = FILE_TEST(sdfitsdir)

if (VERBOSE gt 2) then print,"infileOK    ",infileOK
if (VERBOSE gt 2) then print,"sdfitsdirOK ",sdfitsdirOK

check_for_sdfits_file,infileOK,sdfitsdirOK,infile,beginscan,endscan,VERBOSE

firstScan = fix(beginscan)
lastScan  = fix(endscan)

allscans = indgen(1+lastScan-firstScan) + firstScan
if (VERBOSE gt 2) then print,"allscans ",allscans

if (refscan1 gt -1) and (refscan2 gt -1) then begin & $\
   refscans = [refscan1,refscan2] & endif else begin & $\
   refscans = [firstScan,lastScan] & endelse

if (allscansref ne 0) then refscans=allscans

if (VERBOSE gt 2) then print,"refscans ",refscans

; read in the input file
filein,infile

scanInfo = scan_info(allscans[0])
nFeed = scanInfo.n_feeds
nPol = scanInfo.n_polarizations
nBand = scanInfo.n_ifs

; for each band (spectral window)
wait = 0 ; optionally wait for user input to continue cal
for iFeed = 0, nFeed-1 do begin $\
  for iBand = 0, nBand-1 do begin $\
    gettp,refScans[0], int=0, ifnum=iBand & $\
    calBand, scanInfo, allscans, refscans, iBand, iFeed, nPol, wait & $\
    data_copy, !g.s[0], myDc & $\
    ;select channels and write the AIPS compatible data 
    toaips,myDc,vSource,vSourceWidth,vSourceBegin,vSourceEnd & endfor & endfor