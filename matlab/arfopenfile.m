function [fid] = arfopenfile(filename,mode)
% ARFOPENFILE Open a new ARF file for reading and/or writing
%
% [fid] = ARFOPENFILE(filename,[mode])
%
% The optional argument mode can be 'r' for read-only, 'r+' for
% read-write, or 'w' for truncate mode (default read-only). For 'r'
% modes the file must exist.  For 'w' mode the file will be
% initialized.
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

error(nargchk(1,2,nargin))

if nargin < 2
  mode = 'r';
end

if mode=='r'
  fid = H5F.open(filename, 'H5F_ACC_RDONLY', 'H5P_DEFAULT');
elseif mode=='r+'
  fid = H5F.open(filename, 'H5F_ACC_RDWR', 'H5P_DEFAULT');
elseif mode=='w'
  fid = H5F.create(filename,'H5F_ACC_TRUNC',H5P.create('H5P_FILE_CREATE'),H5P.create('H5P_FILE_ACCESS'));
  init_arf(fid)
else
  error('Invalid mode')
end

function [] = init_arf(fid)
% need to do a bunch of things to make PyTables like the arf file
% root attributes
gid = H5G.open(fid,'/');
make_attr(gid,'TITLE','arf file (ver 1.1.0, created in MATLAB)');
make_attr(gid,'CLASS','GROUP');
make_attr(gid,'PYTABLES_FORMAT_VERSION','2.0');
make_attr(gid,'VERSION','1.0');
make_attr(gid,'arf_version','1.1.0');
H5G.close(gid)

