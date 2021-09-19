<h1 align="center">asciinema-edit 🎬 </h1>

<h5 align="center">Auxiliary tools for dealing with ASCIINEMA casts</h5>

<br/>

`asciinema-edit` is a tool who's purpose is to post-process asciinema casts (V2), either from [asciinema](https://github.com/asciinema/asciinema) itself or [termtosvg](https://github.com/nbedos/termtosvg).

<p align="center">
  <img width="100%" src="/.github/asciinema-edit-overview.svg" alt="Illustration of how ASCIINEMA-EDIT works" />
</p>

Three transformations have been implemented so far:

- [`quantize`](#quantize): Updates the cast delays following quantization ranges; and
- [`cut`](#cut): Removes a certain range of time frames;
- [`speed`](#speed): Updates the cast speed by a certain factor.

Having those, you can improve your cast by:

- speeding up parts that are not very important;
- reducing delays between commands; and
- completely removing parts that don't add value to the cast.

### Installation

Being a Golang application, you can either build it yourself with `go get` or fetch a specific version from the [Releases page](https://github.com/cirocosta/asciinema-edit/releases):

```sh
#Using `go`, fetch the latest from `master`
go get -u -v github.com/cirocosta/asciinema-edit

#Retrieving from GitHub releases
VERSION=0.0.5
curl -SOL https://github.com/cirocosta/asciinema-edit/releases/download/$VERSION/asciinema-edit_$VERSION_linux_amd64.tar.gz
```

### Quantize

```sh
NAME:
   asciinema-edit quantize - Updates the cast delays following quantization ranges.

   The command acts on the delays between the frames, reducing such
   timings to the lowest value defined in a given range that they
   lie in.

   For instance, consider the following timestamps:

      1  2  5  9 10 11

   Assuming that we quantize over [2,6), we'd cut any delays between 2 and
   6 seconds to 2 second:

      1  2  4  6  7  8

   This can be more easily visualized by looking at the delay quantization:

      delta = 1.000000 | qdelta = 1.000000
      delta = 3.000000 | qdelta = 2.000000
      delta = 4.000000 | qdelta = 2.000000
      delta = 1.000000 | qdelta = 1.000000
      delta = 1.000000 | qdelta = 1.000000

   If no file name is specified as a positional argument, a cast is
   expected to be served via stdin.

   Once the transformation has been performed, the resulting cast is
   either written to a file specified in the '--out' flag or to stdout
   (default).

EXAMPLES:
   Make the whole cast have a maximum delay of 1s:

     asciinema-edit quantize --range 2 ./123.cast

   Make the whole cast have time delays between 300ms and 1s cut to
   300ms, delays between 1s and 2s cut to 1s and any delays bigger
   than 2s, cut down to 2s:

     asciinema-edit quantize \
       --range 0.3,1 \
       --range 1,2 \
       --range 2 \
       ./123.cast

USAGE:
   asciinema-edit quantize [command options] [filename]

OPTIONS:
   --range value  quantization ranges (comma delimited)
   --out value    file to write the modified contents to
   
```

### Speed

```sh
NAME:
   asciinema-edit speed - Updates the cast speed by a certain factor.

   If no file name is specified as a positional argument, a cast is
   expected to be served via stdin.

   If no range is specified (start=0, end=0), the whole event stream
   is processed.

   Once the transformation has been performed, the resulting cast is
   either written to a file specified in the '--out' flag or to stdout
   (default).

EXAMPLES:
   Make the whole cast ("123.cast") twice as slow:

     asciinema-edit speed --factor 2 ./123.cast

   Cut the duration in half:

     asciinema-edit speed --factor 0.5 ./123.cast

   Make only a certain part of the video twice as slow:

     asciinema-edit speed \
        --factor 2 \
        --start 12.231 \
        --factor 45.333 \
        ./123.cast

USAGE:
   asciinema-edit speed [command options] [filename]

OPTIONS:
   --factor value  number by which delays are multiplied by (default: 0)
   --start value   initial frame timestamp (default: 0)
   --end value     final frame timestamp (default: 0)
   --out value     file to write the modified contents to
```


### Cut

```sh
NAME:
   asciinema-edit cut - Removes a certain range of time frames.

   If no file name is specified as a positional argument, a cast is
   expected to be served via stdin.

   Once the transformation has been performed, the resulting cast is
   either written to a file specified in the '--out' flag or to stdout
   (default).

EXAMPLES:
   Remove frames from 12.2s to 16.3s from the cast passed in the commands
   stdin.

     cat 1234.cast | \
       asciinema-edit cut \
         --start=12.2 --end=15.3

   Remove the exact frame at timestamp 12.2 from the cast file named
   1234.cast.

     asciinema-edit cut \
       --start=12.2 --end=12.2 \
       1234.cast

USAGE:
   asciinema-edit cut [command options] [filename]

OPTIONS:
   --start value  initial frame timestamp (required) (default: 0)
   --end value    final frame timestamp (required) (default: 0)
   --out value    file to write the modified contents to
```

