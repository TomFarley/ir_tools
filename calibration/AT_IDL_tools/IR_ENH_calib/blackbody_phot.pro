FUNCTION blackbody_phot, temp, lambda_range

;calculate the number of photons emitted by surface at a given temp
;by integrating the blackbody curve

;need to multiply the output by the integration time (at least - maybe solid angle?)

;temp=600 ;temp in kelvin
h=6.63e-34
c=3.0e8
k=1.38e-23

if undefined(lambda_range) then begin
	lambda_range=[4.5e-6, 5.0e-6];MWIR
	lambda_range=[7.6e-6, 8.9e-6];LWIR - taken from Elise's 2010 PSI paper.
	print, lambda_range
endif

lambda=(findgen(1001)/1000)*8e-6

n_phot=((2*!pi*c)/(lambda)^4)*(1/(exp((h*c)/(k*lambda*temp))-1))

;plot, lambda, n_phot

lambda=((findgen(1001)/1000)*(lambda_range[1]-lambda_range[0]))+lambda_range[0]
n_phot=((2*!dpi*c)/(lambda)^4)*(1/(exp((h*c)/(k*lambda*temp))-1))

;oplot, lambda, n_phot, color=truecolor('red')

;print, 'N_phot', int_tabulated(lambda, n_phot)

n_photons=int_tabulated(lambda, n_phot)

;stop

return, n_photons

END
