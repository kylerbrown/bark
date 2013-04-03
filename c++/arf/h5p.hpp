/* @file h5p.hpp
 * @brief C++ arf interface: property lists
 *
 * Copyright (C) 2011-2013 C Daniel Meliza <dan||meliza.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#ifndef _H5P_H
#define _H5P_H 1

#include <hdf5.h>
#include <boost/noncopyable.hpp>
#include "h5e.hpp"

namespace arf { namespace h5p {

class proplist : boost::noncopyable {

public:
	typedef boost::shared_ptr<proplist> ptr_type;

	/** Create a new property list */
	proplist(hid_t cls_id) {
		_self = h5e::check_error(H5Pcreate(cls_id));
	}

        proplist(proplist const & other) {
                _self = h5e::check_error(H5Pcopy(other.hid()));
        };

        proplist & operator= (proplist const & other) {
                H5Pclose(_self);
                _self = h5e::check_error(H5Pcopy(other.hid()));
                return *this;
        }

	~proplist() {
		H5Pclose(_self);
	}

	bool operator==(proplist const & other) const {
		return h5e::check_error(H5Tequal(_self, other.hid()) > 0);
	}
	bool operator!=(proplist const & other) const {
		return h5e::check_error(H5Tequal(_self, other.hid()) <= 0);
	}

	hid_t hid() const { return _self; }
protected:
	hid_t _self;
};

}}

#endif /* _H5P_H */

