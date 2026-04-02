# Nova Inference Engine – Makefile
# Produces nova_engine.so (Linux) or nova_engine.dylib (macOS).

CXX      ?= g++
CXXFLAGS  = -std=c++17 -O3 -march=native -fPIC -Wall -Wextra -DNDEBUG
SRCDIR    = src
INCDIR    = include

UNAME := $(shell uname)
ifeq ($(UNAME), Darwin)
    SOEXT   = dylib
    SOFLAGS = -dynamiclib
else
    SOEXT   = so
    SOFLAGS = -shared
endif

TARGET = nova_engine.$(SOEXT)
OBJS   = nova_engine.o $(SRCDIR)/transformer.o

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(SOFLAGS) -o $@ $^

nova_engine.o: nova_engine.cpp \
               $(INCDIR)/nova_engine.h \
               $(SRCDIR)/transformer.hpp \
               $(SRCDIR)/tensor.hpp \
               $(SRCDIR)/tokenizer.hpp
	$(CXX) $(CXXFLAGS) -I$(INCDIR) -I$(SRCDIR) -c -o $@ $<

$(SRCDIR)/transformer.o: $(SRCDIR)/transformer.cpp \
                          $(SRCDIR)/transformer.hpp \
                          $(SRCDIR)/tensor.hpp \
                          $(SRCDIR)/tokenizer.hpp
	$(CXX) $(CXXFLAGS) -I$(INCDIR) -I$(SRCDIR) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)
