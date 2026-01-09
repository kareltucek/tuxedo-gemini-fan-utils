CC = gcc
CFLAGS = -Wall -O2
TARGET = fanctl

all: $(TARGET)

$(TARGET): fanctl.c
	$(CC) $(CFLAGS) -o $(TARGET) fanctl.c

clean:
	rm -f $(TARGET)

.PHONY: all clean
