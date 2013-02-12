function [] = arfclosefile(fid)
% ARFCLOSEFILE Close an open arf file handle
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

H5F.close(fid)