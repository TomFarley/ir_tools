FUNCTION blackbody_phot_arr, temp, lambda_range

;05/12/18 same as blackbody phot, but for an array rather than a single value

;calculate the number of photons emitted by surface at a given temp
;by integrating the blackbody curve

;need to multiply the output by the integration time (at least - maybe solid angle?)

;temp=600 ;temp in kelvin
h=6.63e-34
c=3.0e8
k=1.38e-23

temp=temp+273. ;convert to Kelvin

if undefined(lambda_range) then begin
	lambda_range=[4.5, 5.0];MWIR
	lambda_range=[7.6, 8.9];LWIR - taken from Elise's 2010 PSI paper.
	print, lambda_range
endif

;print, lambda_range

lr=lambda_range
lr=lr*1e-6 ;go to microns

n_photons=make_array(n_elements(temp))
lambda=((findgen(1001)/1000)*(lr[1]-lr[0]))+lr[0]

for i=0, n_elements(temp)-1 do begin
	n_phot=((2*!dpi*c)/(lambda)^4)*(1/(exp((h*c)/(k*lambda*temp[i]))-1))
	n_photons[i]=int_tabulated(lambda, n_phot)
endfor

return, n_photons

END
