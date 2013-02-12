/* @(#)arf.hpp
 * @brief C++ arf interface
 *
 */

#ifndef _ARF_HH
#define _ARF_HH 1

#include "types.hpp"
#include "arf/h5e.hpp"
#include "arf/h5f.hpp"
#include "arf/h5a.hpp"
#include "arf/h5t.hpp"
#include "arf/h5s.hpp"
#include "arf/h5d.hpp"
#include "arf/h5pt.hpp"
#include <sys/time.h>

#define ARF_LIBRARY_VERSION "2.0.0"

namespace arf {
/*
 * @namespace arf
 *
 * The classes in this namespace define a fairly simple C++ interface
 * for reading and writing ARF files. This consists of a thin wrapper
 * around a more generic HDF5 interface, which is in sub-namespaces of
 * arf. The arf interface simply takes care of setting required
 * attributes, and ensures that data are accessible through the Python
 * and other ARF interfaces.
 *
 * To some extent the HDF5 interface duplicates the existing C++
 * interface shipped with HDF5, but there are some issues compiling it
 * with other features, and quite frankly it's not the best C++
 * interface in the world. The resource model here is focused on
 * safety; objects own the underlying handle to the resources they
 * manage and call the appropriate cleanup function on destruction.
 * Consequently, many of the objects cannot be copied and do not have
 * public constructors.
 *
 *
 */

using h5d::dataset;
using h5pt::packet_table;

namespace h5t { namespace detail {

template<>
struct datatype_traits<interval> {
	static hid_t value() {
                hid_t ret = H5Tcreate(H5T_COMPOUND, sizeof(interval));
                hid_t str = H5Tcopy(H5T_C_S1);
                H5Tset_size(str, 64);
                H5Tinsert(ret, "name", HOFFSET(interval, name), str);
                H5Tinsert(ret, "start", HOFFSET(interval, start), H5T_NATIVE_DOUBLE);
                H5Tinsert(ret, "stop", HOFFSET(interval, stop), H5T_NATIVE_DOUBLE);
                H5Tclose(str);
                return ret;
        }
};

template<>
struct datatype_traits<message> {
	static hid_t value() {
                hid_t str = H5Tcopy(H5T_C_S1);
                H5Tset_size(str, H5T_VARIABLE);
                hid_t ret = H5Tcreate(H5T_COMPOUND, sizeof(arf::message));
                H5Tinsert(ret, "sec", HOFFSET(arf::message, sec), H5T_STD_I64LE);
                H5Tinsert(ret, "usec", HOFFSET(arf::message, usec), H5T_STD_I64LE);
                H5Tinsert(ret, "message", HOFFSET(arf::message, msg), str);
                H5Tclose(str);
                return ret;
        }
};

}}


/**
 * @brief Represents an arf entry.
 *
 * A thin wrapper around h5g::group that creates necessary attributes
 * and provides more convenient dataset creation functions.
 */
class entry : public h5g::group {
public:
	typedef boost::shared_ptr<entry> ptr_type;

	/** Open an existing entry object */
	entry(h5a::node const & parent, std::string const & name)
		: h5g::group(parent, name) {}

	/** Create a new entry object */
	template <typename Type>
	entry(h5a::node const & parent, std::string const & name,
	      std::vector<Type> const & timestamp, boost::uint64_t recid=0)
		: h5g::group(parent, name, true) {
		write_attribute("CLASS","GROUP");
		write_attribute("TITLE",name);
		write_attribute("VERSION","1.0");
		write_attribute<boost::int64_t, Type>("timestamp", timestamp);
		write_attribute("recid", recid);
	}

	entry(h5a::node const & parent, std::string const & name,
	      timeval const * timestamp, boost::uint64_t recid=0)
		: h5g::group(parent, name, true) {
                boost::int64_t ts[2] = { timestamp->tv_sec, timestamp->tv_usec };
		write_attribute("CLASS","GROUP");
		write_attribute("TITLE",name);
		write_attribute("VERSION","1.0");
		write_attribute("timestamp", ts, 2);
		write_attribute("recid", recid);
	}

	/**
	 * Create a new dataset and add data to it.  Currently only 1D
	 * data is supported.
	 *
	 * @param name  the name of the dataset
	 * @param data  the data to store in the dataset
	 * @param units the units of the data
	 * @param datatype an integer code indicating the type of data
	 * @param replace if true, drop existing dataset; otherwise appends data
	 * @param compression integer code indicating compression ratio
	 */
	template <typename StorageType, typename MemType>
	h5d::dataset::ptr_type
	create_dataset(std::string const & name,
		       std::vector<MemType> const & data,
		       std::string const & units,
		       DataType datatype=UNDEFINED,
		       bool replace=false,
		       int compression=0) {
		if (contains(name) && replace)
			unlink(name);

		h5d::dataset::ptr_type ds = h5g::group::create_dataset(name, data, compression);
		ds->write_attribute("CLASS","EARRAY");
		ds->write_attribute("EXTDIM",1);
		ds->write_attribute("VERSION","1.3");
		ds->write_attribute("TITLE",name);
		ds->write_attribute("datatype",static_cast<int>(datatype));
		ds->write_attribute("units",units);
		return ds;
	}

	template <typename Type>
	h5d::dataset::ptr_type
	create_dataset(std::string const & name,
		       std::vector<Type> const & data,
		       std::string const & units,
		       DataType datatype,
		       bool replace=false,
		       int compression=0) {
		return create_dataset<Type,Type>(name,data,units,datatype,replace,compression);
	}

	/**
	 * Create a new packet table dataset. Packet table datasets
	 * are useful for writing a stream of data. No type conversion
	 * is supported, but the interface is extremely simple.
	 *
	 * @param name  the name of the dataset
	 * @param units the units of the data
	 * @param datatype an integer code indicating the type of data
	 * @param replace if true, drop existing dataset; otherwise appends data
	 * @param compression integer code indicating compression ratio
	 */
	template <typename StorageType>
	typename h5pt::packet_table::ptr_type
	create_packet_table(std::string const & name,
			    std::string const & units,
			    DataType datatype,
			    bool replace=false,
			    hsize_t chunk_size=1024,
			    int compression=0) {
                h5pt::packet_table::ptr_type pt =
                        h5g::group::create_packet_table<StorageType>(name, replace, chunk_size, compression);
		pt->write_attribute("CLASS","EARRAY");
		pt->write_attribute("EXTDIM",1);
		pt->write_attribute("VERSION","1.3");
		pt->write_attribute("TITLE",name);
		pt->write_attribute("datatype",static_cast<int>(datatype));
		pt->write_attribute("units",units);
		return pt;
	}

};

/**
 * @brief Represents an arf file.
 *
 * A thin wrapper around h5f::file that creates necessary attributes
 * and provides a more convenient entry accessor
 */
class file : public h5f::file {

public:
	typedef boost::shared_ptr<file> ptr_type;

	/**
	 * Open or create an ARF file.  File access mode can be one
	 * of the following values:
	 * 'r' : read-only; file must exist
	 * 'a' : read-write access, creating file if necessary
	 * 'w' : read-write access; truncates file if it exists
	 *
	 * @param name  the path of the file to open/create
	 * @param mode  the mode to open the file
	 */
	file(std::string const & name, std::string const & mode)
		: h5f::file(name, mode) {
		// set required attributes; I'm too lazy to ensure
		// that the file didn't already exist.
		if (mode=="w" || mode=="a") {
			write_attribute("TITLE","arf file (ver " ARF_LIBRARY_VERSION ", C++)");
			write_attribute("CLASS","GROUP");
			write_attribute("PYTABLES_FORMAT_VERSION","2.0");
			write_attribute("VERSION","1.0");
			write_attribute("arf_version", ARF_LIBRARY_VERSION);
		}
	}

        /**
         * @brief write a message to the log dataset
         *
         * Adds a message to the /log dataset, storing a timestamp and a
         * variable length string. Reading the dataset is not implemented in
         * this interface.
         *
         * @param message  the message to store
         * @param sec      the timestamp of the message (seconds since epoch)
         * @param usec     the timestamp of the message (microseconds)
         */
        void log(std::string const & message, boost::int64_t sec, boost::int64_t usec=0) {
                if (!log_dset) open_log();
                arf::message msg = { sec, usec, message.c_str() };
                log_dset->write(&msg, 1);
        }

        void log(std::string const & message) {
                struct timeval tp;
                gettimeofday(&tp,0);
                log(message, tp.tv_sec, tp.tv_usec);
        }


protected:

        h5pt::packet_table::ptr_type log_dset;

private:
        // generates a log dataset at the top level
        void open_log() {
                if (contains("log")) {
                        try {
                                log_dset.reset(new h5pt::packet_table(_self,"log"));
                        }
                        catch (Exception &e) {
                                throw Exception("/log exists but has wrong type");
                        }
                }
                else {
                        log_dset = create_packet_table<arf::message>("log");
                }
        }

};

}


#endif /* _ARF_H */
