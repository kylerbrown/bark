
CXX=h5c++
CFLAGS=-g2 -Wall -Ic++

all: test

test:	tests/test_arf.cpp
	$(CXX) $(CFLAGS) -o tests/test_arf tests/test_arf.cpp

install:
	find c++ -name "*.hpp" -exec install -m 644 -o root {} /usr/local/include \;
