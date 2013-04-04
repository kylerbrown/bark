/* @(#)hdf5.hpp
 * @brief C++ arf interface: hdf5 C header plus some exceptions, etc
 *
 */

#ifndef _HDF5_HH
#define _HDF5_HH 1

#include <boost/noncopyable.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/make_shared.hpp>
#include <cassert>
#include <string>
#include <stdexcept>

#include <hdf5.h>

namespace arf {

namespace h5f { class file; }

/** Base class for runtime HDF5 errors. */
struct Exception : public std::runtime_error {
	Exception(char const * what) : std::runtime_error(what) { }
};

/**
 * Base class for all hid wrapper objects.  By default these objects
 * are noncopyable, and release the underlying handle on destruction
 */
class handle : boost::noncopyable {
public:
	virtual ~handle() {
		assert(H5Iis_valid(_self) == 0);
	}

	/** Return the path of the object */
	std::string name() const {
		ssize_t sz = H5Iget_name(_self, 0, 0);
		char name[sz+1];
		H5Iget_name(_self, name, sz+1);
		return name;
	}

	/** Return a pointer to the file containing this object */
	boost::shared_ptr<h5f::file> file() const;
	// has to be defined in h5f.hpp

        /**
         * Return the hdf5 identifier. This should be treated like a copy of a
         * pointer; i.e., it will become invalid if the owning object releases
         * the resource.
         */
	hid_t hid() const { return _self; }

        /**
         * Return the hdf5 identifier after increasing the reference count. This
         * means the identifier will remain valid after this object is destroyed.
         */
        hid_t hid_copy() const {
                H5Iinc_ref(_self);
                return _self;
        };

protected:
	/** Protected constructor using hid (or none) */
	handle(hid_t hid=-1) : _self(hid) {}
	hid_t _self;

};

}

#endif /* _TRAITS_HH */
