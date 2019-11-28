PRO plot_nuc, ps=ps

;plotting of the raw images to make some figures for the report

;read in the raw image and the blank image
;plot and then subtract, make three figures 

bck=read_ascii('./IRcam_0101_50mm_20181121/100/bg_50us.ASC')
img=read_ascii('./IRcam_0101_50mm_20181121/100/bb_50us.ASC')

image=img.field001-bck.field001

if keyword_set(ps) then begin
	atpsopen, filename='dark_frame.eps'
	setup_ps
endif else window, 0

cp_shade, bck.field001, zr=[1100,1800], $
	position=[0.15,0.15,0.68,0.9], /iso, /show

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='raw_frame.eps'
	setup_ps
endif else window, 1

cp_shade, img.field001, zr=[1100,2000], $
	position=[0.15,0.15,0.68,0.9], /iso, /show

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='img_frame.eps'
	setup_ps
endif else window,3 

cp_shade, image, zr=[0,400], $
	position=[0.15,0.15,0.68,0.9], /iso, /show

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif


stop

END
