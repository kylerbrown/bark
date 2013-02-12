/* @file types.hpp
 * @brief C++ arf interface: type and forward declarations
 *
 * Copyright (C) 2011 C Daniel Meliza <dan@meliza.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#ifndef _ARF_TYPES_HH
#define _ARF_TYPES_HH 1

#include <boost/cstdint.hpp>
#include <boost/shared_ptr.hpp>
#include <hdf5.h>

namespace arf {

class entry;
typedef boost::shared_ptr<entry> entry_ptr;

class file;
typedef boost::shared_ptr<file> file_ptr;

namespace h5pt {
        class packet_table;
}
typedef boost::shared_ptr<h5pt::packet_table> packet_table_ptr;

/** defines the type of data stored in a dataset */
enum DataType {
	UNDEFINED = 0,
	ACOUSTIC = 1,
	EXTRAC_HP = 2,
	EXTRAC_LF = 3,
	EXTRAC_EEG = 4,
	INTRAC_CC = 5,
	INTRAC_VC = 7,
        EVENT = 1000,
	SPIKET = 1001,
	BEHAVET = 1002,
        INTERVAL = 2000,
	STIMI = 2001,
	COMPONENTL = 2002
};

/**
 * @brief Storage format for interval data
 */
struct interval {
        char name[64];         // could use vlen strings but that's not the spec
        boost::uint32_t start;
        boost::uint32_t stop;
};

/**
 * @brief Storage format for log messages
 */
struct message {
        boost::int64_t sec;
        boost::int64_t usec;
        char const * msg;       // stored as vlen
};

}

#endif
