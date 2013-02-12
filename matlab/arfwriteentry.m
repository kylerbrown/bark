function [] = arfwriteentry(entry_id, name, data, units, datatype,...
                            sampling_rate, storage_type, ...
                            attributes)
% ARFWRITEENTRY write data to an entry
%
% ARFWRITEENTRY (entry_id, name, data, units, datatype, sampling_rate, [storage_type])
%
% Use the entry_id object returned by ARFCREATEENTRY.  Data need to be
% an Mx1 array of sample values. Other data structures are not
% supported by the MATLAB interface.
%
% storage_type can be any HDF5 data type string.  Default is
% H5T_NATIVE_DOUBLE, but H5T_NATIVE_FLOAT, H5T_NATIVE_INT and
% H5T_NATIVE_SHORT are useful for saving space.
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

pdef = 'H5P_DEFAULT';
error(nargchk(7,9,nargin))

if ~isnumeric(data)
  error('Only numeric data types can be stored')
end
[nsamp, nchan] = size(data);

if H5L.exists(entry_id,name,pdef)
  error('The requested node name is already taken')
end

% chunking allows compression. I pick a fixed size (~32k) because
% the intended size of the datasets should be around 1M
dcpl = H5P.create('H5P_DATASET_CREATE');
H5P.set_chunk(dcpl,[4096,1])
H5P.set_deflate(dcpl,1)

if nargin < 8 || isempty(storage_type)
  storage_type = H5T.copy('H5T_NATIVE_DOUBLE');
else
  storage_type = H5T.copy(storage_type);
end

% this is equivalent to a PyTables CArray because it's not expandable
dspace = H5S.create_simple(2,size(data),size(data));
dset_id = H5D.create(entry_id,name,storage_type,dspace,pdef,dcpl,pdef);
H5D.write(dset_id,'H5ML_DEFAULT','H5S_ALL','H5S_ALL',pdef,data');
make_attr(dset_id,'CLASS','CARRAY')
make_attr(dset_id,'TITLE','sampled data')
make_attr(dset_id,'VERSION','1.0')
make_attr(dset_id,'sampling_rate',sampling_rate)
make_attr(dset_id,'units',units)
make_attr(dset_id,'datatype',datatype);
if nargin > 8
  keys = fields(attributes);
  for i = 1:length(keys);
    make_attr(dset_id,keys{i},attributes.(keys{i}));
  end
end
H5S.close(dspace)
H5P.close(dcpl)
H5T.close(storage_type)
H5D.close(dset_id)
