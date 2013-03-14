
CXX=g++
CFLAGS=-g2 -Wall -Ic++ -I/opt/local/include
LDFLAGS=-L/opt/local/lib

all: test

%.o : %.cpp
	$(CXX) $(CFLAGS) -o $@ -c $<

test:	tests/test_arf.o
	$(CXX) $(LDFLAGS) -o tests/test_arf tests/test_arf.o -lhdf5 -lhdf5_hl

clean:
	rm -f test.arf tests/*.o tests/test_arf tests/test.arf

install:
	find c++ -name "*.hpp" -exec install -m 644 -o root {} /usr/local/include \;

