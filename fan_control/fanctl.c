/*
 * fanctl - Simple Tuxedo fan control utility (Clevo interface)
 * Compile: gcc -o fanctl fanctl.c
 * Usage: sudo ./fanctl [status|set <fan> <speed>|auto]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <stdint.h>

#define DEVICE "/dev/tuxedo_io"
#define IOCTL_MAGIC 0xEC
#define MAGIC_READ_CL  (IOCTL_MAGIC + 1)
#define MAGIC_WRITE_CL (IOCTL_MAGIC + 2)

#define R_CL_FANINFO1  _IOR(MAGIC_READ_CL, 0x10, int32_t*)
#define R_CL_FANINFO2  _IOR(MAGIC_READ_CL, 0x11, int32_t*)
#define R_CL_FANINFO3  _IOR(MAGIC_READ_CL, 0x12, int32_t*)
#define W_CL_FANSPEED  _IOW(MAGIC_WRITE_CL, 0x10, int32_t*)
#define W_CL_FANAUTO   _IOW(MAGIC_WRITE_CL, 0x11, int32_t*)

typedef struct {
    int speed;
    int temp1;
    int temp2;
} FanInfo;

int open_device() {
    int fd = open(DEVICE, O_RDWR);
    if (fd < 0) {
        perror("Failed to open " DEVICE);
        fprintf(stderr, "Make sure you're running as root and tuxedo_io module is loaded\n");
        exit(1);
    }
    return fd;
}

int get_fan_info(int fd, int fan_num, FanInfo *info) {
    int32_t faninfo = 0;
    int ret;

    switch (fan_num) {
        case 0: ret = ioctl(fd, R_CL_FANINFO1, &faninfo); break;
        case 1: ret = ioctl(fd, R_CL_FANINFO2, &faninfo); break;
        case 2: ret = ioctl(fd, R_CL_FANINFO3, &faninfo); break;
        default: return -1;
    }

    if (ret < 0) return ret;

    info->speed = faninfo & 0xff;
    info->temp1 = (faninfo >> 8) & 0xff;
    info->temp2 = (faninfo >> 16) & 0xff;

    return 0;
}

void cmd_status(int fd) {
    printf("=== Tuxedo Fan Status ===\n\n");

    const char *fan_names[] = {"CPU", "GPU", "GPU2"};

    for (int i = 0; i < 3; i++) {
        FanInfo info;
        if (get_fan_info(fd, i, &info) == 0) {
            // Skip fans that don't exist (temp2 <= 1 usually means no sensor)
            if (info.temp2 <= 1 && i >= 2) {
                continue;  // Skip fan 2 if not present
            }

            float speed_pct = (info.speed * 100.0) / 255.0;
            printf("Fan %d (%s):\n", i, fan_names[i]);
            printf("  Speed: %.1f%% (raw: %d/255)\n", speed_pct, info.speed);
            printf("  Temp1: %d°C\n", info.temp1);
            printf("  Temp2: %d°C\n", info.temp2);
            printf("\n");
        }
    }
}

void cmd_set(int fd, int fan_num, int speed_pct) {
    if (fan_num < 0 || fan_num > 2) {
        fprintf(stderr, "Error: fan must be 0, 1, or 2\n");
        exit(1);
    }

    if (speed_pct < 0 || speed_pct > 100) {
        fprintf(stderr, "Error: speed must be 0-100\n");
        exit(1);
    }

    // Read current speeds for all fans
    FanInfo fans[3];
    for (int i = 0; i < 3; i++) {
        get_fan_info(fd, i, &fans[i]);
    }

    // Update the specified fan
    fans[fan_num].speed = (speed_pct * 255) / 100;

    // Pack into single value: fan0 | fan1<<8 | fan2<<16
    int32_t argument = (fans[0].speed & 0xff) |
                       ((fans[1].speed & 0xff) << 8) |
                       ((fans[2].speed & 0xff) << 16);

    printf("Setting fan %d to %d%%...\n", fan_num, speed_pct);

    if (ioctl(fd, W_CL_FANSPEED, &argument) < 0) {
        perror("Failed to set fan speed");
        exit(1);
    }

    printf("Done!\n");
}

void cmd_auto(int fd) {
    // Set auto bits for all fans
    int32_t argument = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3);

    printf("Returning fans to automatic control...\n");

    if (ioctl(fd, W_CL_FANAUTO, &argument) < 0) {
        perror("Failed to set auto mode");
        exit(1);
    }

    printf("Done!\n");
}

void usage(const char *prog) {
    printf("Usage:\n");
    printf("  %s status              Show fan status\n", prog);
    printf("  %s set <fan> <speed>   Set fan speed\n", prog);
    printf("  %s auto                Return to automatic control\n", prog);
    printf("\nFan numbers:\n");
    printf("  0 = CPU fan\n");
    printf("  1 = GPU fan\n");
    printf("  (2 = GPU2 fan, if present on your model)\n");
    printf("\nSpeed: 0-100%%\n");
    printf("\nExamples:\n");
    printf("  sudo %s status\n", prog);
    printf("  sudo %s set 0 50       # Set CPU fan to 50%%\n", prog);
    printf("  sudo %s set 1 75       # Set GPU fan to 75%%\n", prog);
    printf("  sudo %s auto\n", prog);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        usage(argv[0]);
        return 1;
    }

    int fd = open_device();

    if (strcmp(argv[1], "status") == 0) {
        cmd_status(fd);
    }
    else if (strcmp(argv[1], "set") == 0) {
        if (argc != 4) {
            fprintf(stderr, "Error: set requires <fan> <speed>\n");
            usage(argv[0]);
            close(fd);
            return 1;
        }
        int fan = atoi(argv[2]);
        int speed = atoi(argv[3]);
        cmd_set(fd, fan, speed);
    }
    else if (strcmp(argv[1], "auto") == 0) {
        cmd_auto(fd);
    }
    else {
        fprintf(stderr, "Error: unknown command '%s'\n", argv[1]);
        usage(argv[0]);
        close(fd);
        return 1;
    }

    close(fd);
    return 0;
}
