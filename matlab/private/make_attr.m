function [] = make_attr(parent_id,name,value)
% MAKE_ATTR Add an attribute to an object and give it a value.
%
% Much of this code is lifted from Mathwork's hdf5tools
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

dataspace_id                     = set_dataspace_id ( value );
datatype_id                      = set_datatype_id ( value );
att_id                           = H5A.create ( parent_id, name, datatype_id, dataspace_id,'H5P_DEFAULT' );
H5A.write(att_id,datatype_id,value);
H5T.close(datatype_id);
H5S.close(dataspace_id);
H5A.close(att_id);


%===============================================================================
% SET_DATASPACE_ID
%
% Setup the dataspace ID.  This just depends on how many elements the
% attribute actually has.
function dataspace_id = set_dataspace_id ( attvalue )

if ischar(attvalue)
    if ( ndims(attvalue) == 2 ) && ( any(size(attvalue) ==1) )
        dataspace_id = H5S.create('H5S_SCALAR');
        return
    elseif ndims(attvalue < 3)
        rank = 1;
        dims = size(attvalue,2);
    else
        error('HDF5TOOLS:h5attput:badStringSize', ...
            'Cannot accept a string input with ndims > 2.');
    end
else
    if prod(size(attvalue))==1
        dataspace_id = H5S.create('H5S_SCALAR');
        return
    end
    if ( ndims(attvalue) == 2 ) && ( any(size(attvalue) ==1) )
        rank = 1;
        dims = numel(attvalue);
    else
        % attribute is a "real" 2D value.
        rank = ndims(attvalue);
	    dims = fliplr(size(attvalue));
    end
end
dataspace_id = H5S.create_simple ( rank, dims, dims );


%===============================================================================
% SET_DATATYPE_ID
%
% We need to choose an appropriate HDF5 datatype based upon the attribute
% data.
function datatype_id = set_datatype_id ( attvalue )
switch class(attvalue)
 case 'double'
  datatype_id = H5T.copy('H5T_NATIVE_DOUBLE');
 case 'single'
  datatype_id = H5T.copy('H5T_NATIVE_FLOAT');
 case 'int64'
  datatype_id = H5T.copy('H5T_NATIVE_LLONG');
 case 'uint64'
  datatype_id = H5T.copy('H5T_NATIVE_ULLONG');
 case 'int32'
  datatype_id = H5T.copy('H5T_NATIVE_INT');
 case 'uint32'
  datatype_id = H5T.copy('H5T_NATIVE_UINT');
 case 'int16'
  datatype_id = H5T.copy('H5T_NATIVE_SHORT');
 case 'uint16'
  datatype_id = H5T.copy('H5T_NATIVE_USHORT');
 case 'int8'
  datatype_id = H5T.copy('H5T_NATIVE_SCHAR');
 case 'uint8'
  datatype_id = H5T.copy('H5T_NATIVE_UCHAR');
 case 'char'
  datatype_id = H5T.copy('H5T_C_S1');
  if any(size(attvalue) == 1)
    H5T.set_size(datatype_id,numel(attvalue));
  else
    H5T.set_size(datatype_id,size(attvalue,1));
  end
  H5T.set_strpad(datatype_id,'H5T_STR_NULLTERM');
 otherwise
  error('MATLAB:H5ATTPUT:unsupportedDatatype', ...
        '''%s'' is not a supported H5ATTPUT datatype.\n', class(attvalue) );
end
return
