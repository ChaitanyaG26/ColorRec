# ColorRec
Two different color recognition programs for the Raspberry Pi: one light-weight, one a bit more "heavy-duty."

We utilized both of these models at some point, leading up to the Aerospace Robotics Competition.

The first of the two is the "contour-stream," which takes a camera frame and outputs a contour-mapped image (this is actually very easy to do on the Pi, we simply take a frame from the camera, compare against HSV min-max arrays, include all the pixels in the same area of a minimum specified area, and draw a bounding box). Then, this image is UPDATED every few miliseconds (fluidity, gives us the illusion that it's a video, but way more efficient in terms of data transmission). This is streamed onto the network hosted by the Pi, which the receiving device must connect to (although you can pair this with ngrok, as we experimented with, as long as your Pi has a constant internet connection, ie through a dongle).

The second of the two is the "text-stream," which does the same as above, but instead of writing a frame to the output website, it simply writes "RED" and changes the background color TO red, which requires even less data transmission.

The way we ran this was by setting up the Pi's own hotspot, configuring this to start on boot, establishing a connection between the receiving device and the Pi via this hotspot (note that the chosen code before should also be configured to start on boot, via daemon-reload and systemctl), and then opening the link to the http:// link with the Pi's IP address to view the stream.