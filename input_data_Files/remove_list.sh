SampleList=( ZGToLLG DYJetsToLL EWKZ2J DYGto2LG_10to50 DYGto2LG_50to100 DYGto2LG_10to100 DYJetsToLL ZG2JToG2L2J TT TTGJets TGJets TTtoLNu2Q WW WZ ZZ WWG WZG ZZG ttZJets ttWJets)
# SampleList=( DYGto2LG_10to50 )
YearList=( 2022preEE 2022postEE 2023preBPix 2023postBPix )

basepath="/eos/project/h/htozg-dy-privatemc/HiggsDNA_skimmed"

for iSample in "${!SampleList[@]}"; do
    for iYear in "${!YearList[@]}"; do
        target="$basepath/${SampleList[iSample]}_${YearList[iYear]}"
        echo "Deleting: $target"
        rm -fr "$target"
    done
done