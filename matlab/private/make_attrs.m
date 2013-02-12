function [] = make_attrs(parent_id, attributes)
% MAKE_ATTRS Add attributes to an object in an hdf5 file
%
% [] = make_attrs(parent_id, attributes)
%
% The <attributes> argument is a structure. Each field is added as
% an attribute.
%
% Copyright (C) 2011 Daniel Meliza <dmeliza@dylan.uchicago.edu>
% Created 2011-04-06

keys = fields(attributes);
for i = 1:length(keys)
  make_attr(parent_id, keys{i}, attributes.(keys{i}));
end

