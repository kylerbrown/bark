function [entry_id] = arfopenentry(fid, entry_name, timestamp, attributes)
% ARFOPENENTRY open an existing entry or create a new entry in an arf file
%
% [entry_id] = ARFOPENENTRY(file_id, entry_name, timestamp, attributes)
%
% Open an arf entry. If the entry does not exist it is created, in
% which case <timestamp> is a required attribute (needs to be a
% two-element array).  Optional attributes are supplied by an optional
% struct supplied to the <attributes> argument.
%
% Make sure to close the entry_id object with H5G.close
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-05

% check that the entry doesn't exist; if it does just open it
if H5L.exists(fid,entry_name,'H5P_DEFAULT')
  entry_id = H5G.open(fid,entry_name);
  return
end

error(nargchk(3,4,nargin))
if nargin < 4
  attributes = struct;
end

root = H5G.open(fid,'/');

% add the group
entry_id = H5G.create(root,entry_name,'H5P_DEFAULT','H5P_DEFAULT','H5P_DEFAULT');
H5G.close(root)
% add attributes to group
make_attr(entry_id,'CLASS','GROUP')
make_attr(entry_id,'TITLE',entry_name)
make_attr(entry_id,'VERSION','1.0')
make_attr(entry_id,'recid',uint64(0))
make_attr(entry_id,'timestamp',int64(timestamp))
keys = fields(attributes);
for i = 1:numel(keys)
  key = keys{i};
  make_attr(entry_id,key,attributes.(key))
end
