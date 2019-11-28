PRO test_data, ps=ps

;=====================================================
;Altair

bgname='background_100.asc'
bbname='image_100.asc'

tmp=read_ascii(bgname, delimiter=' ', data_start=29)
bg=tmp.field001
tmp=read_ascii(bbname, delimter=' ', data_start=29)
bb=tmp.field001

img=bb-bg

window, 0
cp_shade, img, /iso, /show

;======================================================
;ResearchIR

bgname='test_bg_filter1.csv'
bbname='test_image_filter1.csv'

tmp=read_ascii(bgname, delimiter=',', data_start=31)
bg2=tmp.field001
tmp=read_ascii(bbname, delimiter=',', data_start=31)
bb2=tmp.field001

img2=bb2-bg2

window, 1
cp_shade, img2, /iso, /show



stop

END
