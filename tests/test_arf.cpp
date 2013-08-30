/* @file test.cpp
 *
 * Copyright (C) 2011-2013 C Daniel Meliza <dan||meliza.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#include <iostream>
#include <vector>
#include <unistd.h>
#include <sys/time.h>
#include "arf.hpp"

struct interval {
        char name[64];
        boost::uint32_t start;
        boost::uint32_t stop;
};

namespace arf { namespace h5t { namespace detail {

template<>
struct datatype_traits<interval> {
	static hid_t value() {
                hid_t ret = H5Tcreate(H5T_COMPOUND, sizeof(interval));
                hid_t str = H5Tcopy(H5T_C_S1);
                H5Tset_size(str, 64);
                H5Tinsert(ret, "name", HOFFSET(interval, name), str);
                H5Tinsert(ret, "start", HOFFSET(interval, start), H5T_STD_U32LE);
                H5Tinsert(ret, "stop", HOFFSET(interval, stop), H5T_STD_U32LE);
                H5Tclose(str);
                return ret;
        }
};

}}}

unsigned short seed[3] = { 0 };
const int nsamples = 1 << 12;
const int nentries = 1 << 8;
const int npackets = 5;

struct timeval tp;
int testval_int = 1;
std::vector<int> testval_intvec(5,10);
char const * testval_str = "blahdeblah";
std::vector<float> testval_floatvec(nsamples);
interval testval_interval = { "label_%03d", 0, 123};


void write_entry(arf::file & f, char const * entry) {

	gettimeofday(&tp,0);
	arf::entry g(f,entry,tp.tv_sec,tp.tv_usec);

        // check that stored uuid matches created one
        arf::entry gg(f,entry);
        assert (gg.uuid() == g.uuid());

	g.write_attribute()
                ("intattr",testval_int)
                ("vecattr",testval_intvec)
                ("strattr",testval_str);
}

void write_sampled(arf::file & f, char const * entry) {
        arf::entry g(f, entry);
	arf::dataset_ptr d = g.create_dataset<double>("dataset", testval_floatvec, "mV", arf::ACOUSTIC);
	d->write_attribute("sampling_rate",1000);
}

void write_packettbl(arf::file & f, char const * entry) {
        arf::entry g(f, entry);
	arf::packet_table_ptr pt =
		g.create_packet_table<float>("apackettable","mV",arf::ACOUSTIC);
	pt->write_attribute("sampling_rate",1000);
        for (int i = 0; i < npackets; ++i)
                pt->write(testval_floatvec);
}

void write_interval(arf::file & f, char const *entry) {
        arf::entry g(f, entry);
        arf::packet_table_ptr pt =
                g.create_packet_table<interval>("intervals","ms",arf::STIMI);
        interval data = testval_interval;
        for (int i = 0; i < npackets; ++i) {
                sprintf(data.name, testval_interval.name, i);
                data.start += 100;
                data.stop += 100;
                pt->write(&data, 1);
        }
}

void read_entry(arf::h5f::file & f, char const * entry) {
	arf::entry g(f,entry);
        arf::h5a::attribute a(g,"intattr");
        assert (a.name() == "intattr");
        assert (a.read<int>() == testval_int);
        assert (g.read_attribute<std::string>("strattr") == testval_str);

        std::vector<int> readvec;
        g.read_attribute("vecattr", readvec);
        assert (std::equal(readvec.begin(), readvec.end(), testval_intvec.begin()));

}

void read_sampled(arf::h5f::file & f, char const * entry) {
	arf::entry g(f,entry);
        float buf[nsamples];

        g.read_dataset("dataset",buf, nsamples);
        assert (std::equal(buf, buf + nsamples, testval_floatvec.begin()));
}

void read_packettbl(arf::h5f::file & f, char const * entry) {
	arf::entry g(f,entry);
        float buf[nsamples];

        // read at offset
        g.read_dataset("apackettable",buf,nsamples/2,nsamples);
        assert (std::equal(buf, buf + nsamples/2, testval_floatvec.begin()));
}

int
main(int argc, char ** argv)
{
        int i;

        for (i = 0; i < nsamples; ++i)
                testval_floatvec[i] = nrand48(seed);

        {
                arf::file f("test.arf","w");
                assert (f.name() == "test.arf");

                char ename[64];

                for (i = 0; i < nentries; ++i) {
                        sprintf(ename, "entry_%03d", nentries - i - 1);
                        write_entry(f, ename);
                        write_sampled(f, ename);
                        write_packettbl(f, ename);
                        write_interval(f, ename);
                }
                std::cout << "Finished creating " << f.nchildren() << " entries" << std::endl;
                f.children();  // make sure iteration works

                std::cout << "File size after writes:" << f.size() << std::endl;

                // test concurrent access
                arf::h5f::file g("test.arf","a");
                assert(g.children() == f.children());
        }

        {
                arf::h5f::file f("test.arf","r");
                std::cout << "File size after flush:" << f.size() << std::endl;
                char ename[64];

                for (i = 0; i < nentries; ++i) {
                        sprintf(ename, "entry_%03d", i);
                        read_entry(f, ename);
                        read_sampled(f, ename);
                        read_packettbl(f, ename);
                }
        }

        // try some error conditions
        bool flag = false;
        try {
                arf::h5f::file f("nosuchfile.arf","r");
        }
        catch (arf::Exception &e) {
                flag = true;
        }
        assert(flag);

        std::cout << "Passed all tests" << std::endl;
	return 0;
}
