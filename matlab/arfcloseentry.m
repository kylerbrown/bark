function [] = arfcloseentry(fid)
% ARFCLOSEENTRY Close an open arf entry handle
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

H5G.close(fid)